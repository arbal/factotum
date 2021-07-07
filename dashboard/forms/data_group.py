import ast
import itertools
import uuid
from datetime import datetime

from django.utils import timezone

from django import forms
from django.db import transaction
from django.db.models import CharField, Value as V

from django.db.models.functions import Cast, Concat

from bulkformsets import BaseBulkFormSet, CSVReader
from celery_formtask.forms import FormTaskMixin

from dashboard.models import (
    DataDocument,
    Product,
    DuplicateProduct,
    ProductDocument,
    Script,
    ExtractedComposition,
    FunctionalUse,
    FunctionalUseCategory,
    DataGroup,
    RawChem,
    ExtractedText,
    ExtractedCPCat,
    UnitType,
    ExtractedFunctionalUse,
    ExtractedListPresence,
    WeightFractionType,
    ExtractedLMDoc,
    ExtractedLMRec,
)
from dashboard.models.extracted_lmrec import (
    StatisticalValue,
    HarmonizedMedium,
    GENDER_CHOICES,
    TYPE_CHOICES,
)
from dashboard.models.functional_use import FunctionalUseToRawChem

from dashboard.utils import (
    clean_dict,
    get_extracted_models,
    field_for_model,
    get_missing_ids,
    inheritance_bulk_create,
)
from factotum.environment import env


class DGFormSet(BaseBulkFormSet):
    extra = 0
    can_order = False
    can_delete = False
    min_num = 1
    max_num = 50000
    absolute_max = 50000
    validate_min = True
    validate_max = True


class UploadDocsForm(forms.Form):
    prefix = "uploaddocs"
    documents = forms.FileField()

    def __init__(self, dg, *args, **kwargs):
        self.dg = dg
        super().__init__(*args, **kwargs)

    def clean(self):
        if len(self.files.getlist("%s-documents" % self.prefix)) > 600:
            raise forms.ValidationError("Please limit upload to 600 files.")
        self.file_dict = {
            f.name: f for f in self.files.getlist("%s-documents" % self.prefix)
        }
        self.datadocuments = DataDocument.objects.filter(
            data_group=self.dg, filename__in=self.file_dict.keys()
        )
        if not self.datadocuments.exists():
            raise forms.ValidationError(
                "There are no matching filenames in the directory selected."
            )

    def save(self):
        with transaction.atomic():
            for doc in self.datadocuments:
                doc.file = self.file_dict[doc.filename]
                doc.save()

        return self.datadocuments.count()


class ProductCSVForm(forms.Form):
    """ A form based on the Product object
    but with the addition of data_document_id and
    data_document_filename fields
    """

    data_document_id = field_for_model(ProductDocument, "document_id")
    data_document_filename = field_for_model(DataDocument, "filename")
    title = field_for_model(Product, "title")
    upc = field_for_model(Product, "upc", required=False)
    url = field_for_model(Product, "url")
    brand_name = field_for_model(Product, "brand_name")
    size = field_for_model(Product, "size")
    color = field_for_model(Product, "color")
    item_id = field_for_model(Product, "item_id")
    parent_item_id = field_for_model(Product, "parent_item_id")
    short_description = field_for_model(Product, "short_description")
    long_description = field_for_model(Product, "long_description")
    epa_reg_number = field_for_model(Product, "epa_reg_number")
    thumb_image = field_for_model(Product, "thumb_image")
    medium_image = field_for_model(Product, "medium_image")
    large_image = field_for_model(Product, "large_image")
    model_number = field_for_model(Product, "model_number")
    manufacturer = field_for_model(Product, "manufacturer")
    image_name = forms.CharField(required=False)


class ProductBulkCSVFormSet(DGFormSet):
    """
    Multiple products can be created for a single document.
    If user attempts to upload product data for a document
    which already has an associated product, a new product
    is created with the newly uploaded data (rather than
    trying to insert data into the existing product record).
    If a user uploads a product file which includes multiple
    rows for a single data document ID, each row should be
    assumed to be a different product for that document
    """

    prefix = "products"
    serializer = CSVReader
    form = ProductCSVForm
    header_cols = [
        "data_document_id",
        "data_document_filename",
    ] + DataGroup().get_product_template_fieldnames()

    def clean(self, *args, **kwargs):
        missing_images = []
        oversize_images = []
        directory_size = 0
        # Directory Max file count error
        if (
            len(self.files.getlist("products-bulkformsetimageupload"))
            > env.PRODUCT_IMAGE_DIRECTORY_MAX_FILE_COUNT
        ):
            raise forms.ValidationError(
                "The image directory has too many files.  "
                "Please reduce the number of document upload at one time to < %d."
                % env.PRODUCT_IMAGE_DIRECTORY_MAX_FILE_COUNT
            )
        self.image_dict = {
            f.name: f for f in self.files.getlist("products-bulkformsetimageupload")
        }
        # Image Upload is too large
        for file_name in self.image_dict:
            directory_size += self.image_dict[file_name].size
            if self.image_dict[file_name].size > env.PRODUCT_IMAGE_MAX_SIZE:
                oversize_images.append(file_name)
        # Directory too large error
        if directory_size > env.PRODUCT_IMAGE_DIRECTORY_MAX_UPLOAD:
            raise forms.ValidationError(
                "The image directory is too large.  "
                "Please reduce the size of the directory to < %d MB"
                % (env.PRODUCT_IMAGE_DIRECTORY_MAX_UPLOAD / 1000000)
            )
        # Images too large error
        if oversize_images:
            raise forms.ValidationError(
                "The following images are too large.  "
                "Please reduce their sizes to < %d MB: "
                % (env.PRODUCT_IMAGE_MAX_SIZE / 1000000)
                + ", ".join([image for image in oversize_images])
            )
        # No Image match error
        for f in self.forms:
            image_name = f.cleaned_data["image_name"]
            if image_name and not image_name in self.image_dict.keys():
                missing_images.append(str(f.cleaned_data["data_document_id"].pk))
        if missing_images:
            report = (
                "The following record images could not be matched.  "
                "Please correct or remove their image_names and retry the upload: "
            )
            report += ", ".join(missing_images)
            raise forms.ValidationError(report)
        header = list(self.bulk.fieldnames)
        if header != self.header_cols:
            raise forms.ValidationError(
                f"CSV column titles should be {self.header_cols}"
            )

        # Iterate over the formset to accumulate the UPCs and check for duplicates
        upcs = [f.cleaned_data["upc"] for f in self.forms if f.cleaned_data.get("upc")]

        seen = {}
        # The original list of duplicated UPCs should include all the ones
        # already in the database that appear in the uploaded file. All the
        # new UPCs are added as well in order to check for in-file duplication
        self.dupe_upcs = list(
            Product.objects.filter(upc__in=upcs)
            .values_list("upc", flat=True)
            .distinct()
        )
        for x in upcs:
            if x not in seen:
                seen[x] = 1
            else:
                if seen[x] == 1:
                    self.dupe_upcs.append(x)
                seen[x] += 1

    def save(self):
        rejected_docids = []
        reports = []
        added_products = 0

        for f in self.forms:
            f.cleaned_data["created_at"] = datetime.now()
            image_name = f.cleaned_data.pop("image_name")
            product_dict = clean_dict(f.cleaned_data, Product)
            # if the UPC is already in the database, add the product
            # to the DuplicateProduct model and report it.
            # It does not invalidate the formset
            if product_dict.get("upc") in self.dupe_upcs:
                # Move the source file's duplicate UPC to the source_upc field
                product_dict.update(source_upc=product_dict.get("upc"))
                # replace the incoming UPC with a UUID
                product_dict.update(upc=uuid.uuid4())
                # Create the new record
                product = DuplicateProduct(**product_dict)
                # attach the image if there is one
                if image_name:
                    product.image = self.image_dict[image_name]
                product.save()
                # once the product is created, it can be linked to
                # a DataDocument via the ProductDocument table
                productdocument = ProductDocument(
                    product=product, document=f.cleaned_data["data_document_id"]
                )
                productdocument.save()

                rejected_docids.append(f.cleaned_data["data_document_id"].pk)
            else:
                # add the new product to the database
                product = Product(**product_dict)
                # attach the image if there is one
                if image_name:
                    product.image = self.image_dict[image_name]
                product.save()
                # once the product is created, it can be linked to
                # a DataDocument via the ProductDocument table
                productdocument = ProductDocument(
                    product=product, document=f.cleaned_data["data_document_id"]
                )
                productdocument.save()
                added_products += 1

        if len(rejected_docids) > 0:
            report = f"The following data documents had existing or duplicated UPCs and their new products were added as duplicates: "
            report += ", ".join("%d" % i for i in rejected_docids)
            reports.append(report)
        return added_products, reports


class BaseExtractFileForm(forms.Form):
    extraction_script = forms.IntegerField(required=True)
    data_document_id = forms.IntegerField(required=True)
    doc_date = field_for_model(ExtractedText, "doc_date")
    raw_category = field_for_model(DataDocument, "raw_category")
    raw_cas = field_for_model(RawChem, "raw_cas")
    raw_chem_name = field_for_model(RawChem, "raw_chem_name")
    report_funcuse = forms.CharField(required=False)

    def clean(self):
        super().clean()
        data = self.cleaned_data
        # Rename fields
        data["extraction_script_id"] = data.pop("extraction_script")
        data["extracted_text_id"] = data.get("data_document_id")
        # Validate model
        params = clean_dict(self.cleaned_data, ExtractedText)
        ExtractedText(**params).clean()


class FunctionalUseExtractFileForm(BaseExtractFileForm):
    prod_name = field_for_model(ExtractedText, "prod_name")
    rev_num = field_for_model(ExtractedText, "rev_num")

    def clean(self):
        super().clean()
        params = clean_dict(self.cleaned_data, ExtractedFunctionalUse)
        obj = ExtractedFunctionalUse(**params)
        obj.clean()
        obj.validate_unique()


class CompositionExtractFileForm(BaseExtractFileForm):
    prod_name = field_for_model(ExtractedText, "prod_name")
    rev_num = field_for_model(ExtractedText, "rev_num")
    raw_min_comp = field_for_model(ExtractedComposition, "raw_min_comp")
    raw_max_comp = field_for_model(ExtractedComposition, "raw_max_comp")
    unit_type = forms.IntegerField(required=False)
    ingredient_rank = field_for_model(ExtractedComposition, "ingredient_rank")
    raw_central_comp = field_for_model(ExtractedComposition, "raw_central_comp")
    component = field_for_model(ExtractedComposition, "component")

    def clean(self):
        super().clean()
        data = self.cleaned_data
        # Rename fields
        data["unit_type_id"] = data.pop("unit_type")
        # Validate model
        params = clean_dict(self.cleaned_data, ExtractedComposition)
        obj = ExtractedComposition(**params)
        obj.clean()
        obj.validate_unique()


class ChemicalPresenceExtractFileForm(BaseExtractFileForm):
    cat_code = field_for_model(ExtractedCPCat, "cat_code")
    description_cpcat = field_for_model(ExtractedCPCat, "description_cpcat")
    cpcat_code = field_for_model(ExtractedCPCat, "cpcat_code")
    cpcat_sourcetype = field_for_model(ExtractedCPCat, "cpcat_sourcetype")
    component = field_for_model(ExtractedListPresence, "component")
    chem_detected_flag = field_for_model(RawChem, "chem_detected_flag")

    def clean(self):
        super().clean()
        data = self.cleaned_data
        params = clean_dict(data, ExtractedCPCat)
        obj = ExtractedCPCat(**params)
        obj.clean()
        obj.validate_unique()
        params = clean_dict(data, ExtractedListPresence)
        obj = ExtractedListPresence(**params)
        obj.clean()
        obj.validate_unique()


class LiteratureMonitorExtractFileForm(BaseExtractFileForm):
    prod_name = field_for_model(ExtractedText, "prod_name")
    rev_num = field_for_model(ExtractedText, "rev_num")
    study_type = field_for_model(ExtractedLMDoc, "study_type")
    media = field_for_model(ExtractedLMDoc, "media")
    qa_flag = field_for_model(ExtractedLMDoc, "qa_flag")
    qa_who = field_for_model(ExtractedLMDoc, "qa_who")
    extraction_wa = field_for_model(ExtractedLMDoc, "extraction_wa")
    chem_detected_flag = field_for_model(RawChem, "chem_detected_flag")
    study_location = field_for_model(ExtractedLMRec, "study_location")
    sampling_date = field_for_model(ExtractedLMRec, "sampling_date")
    population_description = field_for_model(ExtractedLMRec, "population_description")
    population_gender = field_for_model(ExtractedLMRec, "population_gender")
    population_age = field_for_model(ExtractedLMRec, "population_age")
    population_other = field_for_model(ExtractedLMRec, "population_other")
    sampling_method = field_for_model(ExtractedLMRec, "sampling_method")
    analytical_method = field_for_model(ExtractedLMRec, "analytical_method")
    medium = field_for_model(ExtractedLMRec, "medium")
    harmonized_medium = forms.CharField(required=False)
    num_measure = field_for_model(ExtractedLMRec, "num_measure")
    num_nondetect = field_for_model(ExtractedLMRec, "num_nondetect")
    detect_freq = field_for_model(ExtractedLMRec, "detect_freq")
    detect_freq_type = field_for_model(ExtractedLMRec, "detect_freq_type")
    LOD = field_for_model(ExtractedLMRec, "LOD")
    LOQ = field_for_model(ExtractedLMRec, "LOQ")
    statistical_values = forms.CharField(required=False)

    def clean(self):
        super().clean()
        data = self.cleaned_data
        params = clean_dict(data, ExtractedLMDoc)
        obj = ExtractedLMDoc(**params)
        obj.clean()
        obj.validate_unique()

        # set harmonized medium from name string
        hm = data.pop("harmonized_medium", None)
        if hm:
            hm_obj = HarmonizedMedium.objects.filter(name=hm).first()
            if hm_obj:
                data["harmonized_medium"] = hm_obj
            else:
                self.add_error(
                    "harmonized_medium",
                    forms.ValidationError(
                        f"Select a valid choice. {hm} is not one of the available choices."
                    ),
                )

        # parse and set statistical values
        statistics = data.pop("statistical_values", None)
        data["statistical_values"] = []
        if statistics:
            stat_strings = [stat.strip() for stat in statistics.split(";")]
            for stat in stat_strings:
                if stat:
                    stat_map = ast.literal_eval(stat)
                    stat_val = StatisticalValue(**stat_map)
                    stat_val.clean()
                    # validate statistical value fields
                    valid_types = []
                    for k, v in TYPE_CHOICES:
                        valid_types.append(k)
                    has_error = False
                    if stat_val.value_type and stat_val.value_type not in valid_types:
                        self.add_error(
                            "statistical_values",
                            forms.ValidationError(
                                f"Invalid value_type choice. {stat_val.value_type} is not one of the available choices."
                            ),
                        )
                        has_error = True
                    if not stat_val.value_type:
                        self.add_error(
                            "statistical_values",
                            forms.ValidationError("value_type field is required"),
                        )
                        has_error = True
                    if not stat_val.name:
                        self.add_error(
                            "statistical_values",
                            forms.ValidationError("name field is required"),
                        )
                        has_error = True
                    if stat_val.value is None or str(stat_val.value) == "":
                        self.add_error(
                            "statistical_values",
                            forms.ValidationError("value field is required"),
                        )
                        has_error = True
                    if not stat_val.stat_unit:
                        self.add_error(
                            "statistical_values",
                            forms.ValidationError("stat_unit field is required"),
                        )
                        has_error = True
                    if not has_error:
                        data["statistical_values"].append(stat_val)

        params = clean_dict(data, ExtractedLMRec)
        obj = ExtractedLMRec(**params)
        obj.clean()
        obj.validate_unique()


class ExtractFileFormSet(FormTaskMixin, DGFormSet):
    prefix = "extfile"
    header_fields = ["extraction_script"]
    serializer = CSVReader

    def __init__(self, *args, dgpk=None, **kwargs):
        # We seem to be doing nothing with DataDocument.filename even though it's
        # being collected.
        dg = DataGroup.objects.get(pk=dgpk)
        self.dg = dg
        if dg.type == "FU":
            self.form = FunctionalUseExtractFileForm
        elif dg.type == "CO":
            self.form = CompositionExtractFileForm
        elif dg.type == "CP":
            self.form = ChemicalPresenceExtractFileForm
        elif dg.type == "LM":
            self.form = LiteratureMonitorExtractFileForm
        # For the template render
        self.extraction_script_choices = [
            (str(s.pk), str(s))
            for s in Script.objects.filter(script_type="EX").filter(qa_begun=False)
        ]
        super().__init__(*args, dgpk=dgpk, ignored_kwargs=["dgpk"], **kwargs)

    def clean(self):
        validation_errors = []
        # We're now CPU bound on this call, not SQL bound. Make for a more fun problem.
        Parent, Child = get_extracted_models(self.dg.type)
        unique_parent_ids = set(f.cleaned_data["data_document_id"] for f in self.forms)
        # Check that extraction_script is valid
        extraction_script_id = self.forms[0].cleaned_data["extraction_script_id"]
        if not Script.objects.filter(
            script_type="EX", pk=extraction_script_id
        ).exists():
            err = forms.ValidationError("Invalid extraction script selection.")
            validation_errors.append(err)
        # Check that unit_type is valid
        unit_type_ids = (
            f.cleaned_data["unit_type_id"]
            for f in self.forms
            if f.cleaned_data.get("unit_type_id") is not None
        )
        bad_ids = get_missing_ids(UnitType, unit_type_ids)
        if bad_ids:
            err_str = 'The following "unit_type"s were not found: '
            err_str += ", ".join("%d" % i for i in bad_ids)
            err = forms.ValidationError(err_str)
            validation_errors.append(err)
        # Check that the data_document_id are all valid
        datadocument_dict = DataDocument.objects.filter(data_group=self.dg).in_bulk(
            unique_parent_ids
        )
        if len(datadocument_dict) != len(unique_parent_ids):
            bad_ids = unique_parent_ids - datadocument_dict.keys()
            err_str = (
                'The following "data_document_id"s were not found for this data group: '
            )
            err_str += ", ".join("%d" % i for i in bad_ids)
            err = forms.ValidationError(err_str)
            validation_errors.append(err)
        # Check that parent fields do not conflict (OneToOne check)
        if hasattr(Parent, "cat_code"):
            oto_field = "cat_code"
        elif hasattr(Parent, "prod_name"):
            oto_field = "prod_name"
        else:
            oto_field = None
        if oto_field:
            unique_parent_oto_fields = set(
                (f.cleaned_data["data_document_id"], f.cleaned_data[oto_field])
                for f in self.forms
            )
            if len(unique_parent_ids) != len(unique_parent_oto_fields):
                unseen_parents = set(unique_parent_ids)
                bad_ids = []
                for i, _ in unique_parent_oto_fields:
                    if i in unseen_parents:
                        unseen_parents.remove(i)
                    else:
                        bad_ids.append(i)
                err_str = (
                    'The following "data_document_id"s got unexpected "%s"s (must be 1:1): '
                    % oto_field
                )
                err_str += ", ".join("%d" % i for i in bad_ids)
                err = forms.ValidationError(err_str)
                validation_errors.append(err)
        if validation_errors:
            raise forms.ValidationError(validation_errors)
        # Make the DataDocument, Parent, and Child objects and validate them
        parent_dict = Parent.objects.in_bulk(unique_parent_ids)
        unseen_parents = set(unique_parent_ids)
        for form in self.forms:
            data = form.cleaned_data
            pk = data["data_document_id"]
            # Parent and DataDocument
            if pk in unseen_parents:
                # DataDocument updates
                datadocument = datadocument_dict[pk]
                new_raw_category = data["raw_category"]
                old_raw_category = datadocument.raw_category
                if new_raw_category != old_raw_category:
                    datadocument.raw_category = new_raw_category
                    datadocument.clean(skip_type_check=True)
                    datadocument._meta.created_fields = {}
                    datadocument._meta.updated_fields = {
                        "raw_category": {
                            "old": old_raw_category,
                            "new": new_raw_category,
                        }
                    }
                else:
                    datadocument._meta.created_fields = {}
                    datadocument._meta.updated_fields = {}
                # Parent creates
                parent_params = clean_dict(data, Parent)
                if pk not in parent_dict:
                    parent = Parent(**parent_params)
                    parent._meta.created_fields = parent_params
                    parent._meta.updated_fields = {}
                # Parent updates
                else:
                    parent = parent_dict[pk]
                    parent._meta.created_fields = {}
                    parent._meta.updated_fields = {}
                    for field, new_value in parent_params.items():
                        old_value = getattr(parent, field)
                        if new_value != old_value:
                            setattr(parent, field, new_value)
                            parent._meta.updated_fields[field] = {
                                "old_value": old_value,
                                "new_value": new_value,
                            }
                # Mark this parent as seen
                unseen_parents.remove(pk)
            else:
                parent = None
                datadocument = None
            # Child creates
            child_params = clean_dict(data, Child)
            if form["report_funcuse"].value():
                use_vals = [
                    u.strip() for u in form["report_funcuse"].value().split(";")
                ]
            else:
                use_vals = []
            existing_uses = None
            new_uses = None
            # Only include children if relevant data is attached
            if child_params.keys() - {"extracted_text_id"}:
                child = Child(**child_params)
                child._meta.created_fields = child_params
                child._meta.updated_fields = {}
                uses = []
                for use in use_vals:
                    if not use:  # filter out empty strings
                        continue
                    elif len(use) > 255:
                        form.add_error(
                            "report_funcuse",
                            forms.ValidationError(
                                "The reported functional use string is too long"
                            ),
                        )
                    else:
                        uses.append(use.lower())

                # Get existing functional uses
                existing_uses = list(
                    FunctionalUse.objects.filter(report_funcuse__in=uses)
                )

                # Get new (to be created) functional uses
                new_uses = set(uses)
                new_uses.difference(set(map(lambda o: o.report_funcuse, existing_uses)))

            else:
                child = None
            if (
                (existing_uses or new_uses)
                and not self.dg.can_have_multiple_funcuse
                and (len(existing_uses) + len(new_uses)) > 1
            ):
                # Get a list of all uses
                uses = existing_uses
                uses.extend(new_uses)

                form.add_error(
                    "report_funcuse",
                    forms.ValidationError(
                        "No more than one functional use is acceptable."
                        f" Reported uses: {[str(u) for u in uses]}"
                    ),
                )
            # Store in dictionary
            data["datadocument"] = datadocument
            data["parent"] = parent
            data["child"] = child
            data["uses"] = existing_uses
            data["new_uses"] = new_uses

    def save(self):
        datadocuments = [
            f.cleaned_data["datadocument"]
            for f in self.forms
            if f.cleaned_data["datadocument"]
        ]
        parents = [
            f.cleaned_data["parent"] for f in self.forms if f.cleaned_data["parent"]
        ]
        children = [
            f.cleaned_data["child"] for f in self.forms if f.cleaned_data["child"]
        ]
        # Functional Uses are organized as a list of lists.
        # The external list is the document list (parent).
        # The internal lists are the content for the chemical (child).
        # Set of existing FunctionalUses that are already added to the database.
        funcuses = [
            f.cleaned_data["uses"] for f in self.forms if f.cleaned_data["child"]
        ]
        # Set of new rawchem terms to be added to the database.
        new_funcuses = [
            f.cleaned_data["new_uses"] for f in self.forms if f.cleaned_data["child"]
        ]

        # Set of statistical values for lm record
        statistical_values = []
        for f in self.forms:
            if "statistical_values" in f.cleaned_data.keys():
                statistical_values.append(f.cleaned_data["statistical_values"])

        with transaction.atomic():
            # Abstract some of the funcuse info out of the save.
            # Creates FunctionalUses for all new_funcuses report_funcuse strings
            # and combines them with the corresponding set of FunctionalUses in
            # funcuses.
            funcuses = self._create_new_functional_uses(funcuses, new_funcuses)

            # Update DataDocument and Parent
            for objs in (datadocuments, parents):
                updated_objs = [o for o in objs if o._meta.updated_fields]
                updated_fields = {"updated_at"}
                for obj in updated_objs:
                    updated_fields |= set(obj._meta.updated_fields.keys())
                    obj.updated_at = timezone.now()
                if updated_objs:
                    model = updated_objs[0]._meta.model
                    model.objects.bulk_update(updated_objs, updated_fields)
            # Create Parent and Child
            for objs in (parents, children):
                created_objs = [o for o in objs if o._meta.created_fields]
                if created_objs:
                    chems = inheritance_bulk_create(created_objs)
            # Bulk add functional uses to each chemical.
            reported_uses = []
            for chem, uses in zip(chems, funcuses):
                for use in uses:
                    reported_uses.append(
                        FunctionalUseToRawChem(functional_use=use, chemical_id=chem.pk)
                    )
            # Add all new connections at once.
            FunctionalUseToRawChem.objects.bulk_create(reported_uses)

            # create all statistic values
            statistics = []
            for chem, stats in zip(chems, statistical_values):
                for stat in stats:
                    stat.record = chem
                    statistics.append(stat)
            StatisticalValue.objects.bulk_create(statistics)
        return len(self.forms)

    def _create_new_functional_uses(self, funcuses, new_funcuses):
        """Creates functional uses for strings in new_funcuses and adds them to
        funcuses.  Returns list of lists containing all funcuses"""

        # Save the new functional uses.
        # Flattened with itertools then bulk create all rows. (one sql operation)
        flat_report_funcuses = set(itertools.chain(*new_funcuses))
        FunctionalUse.objects.bulk_create(
            [FunctionalUse(report_funcuse=use) for use in flat_report_funcuses]
        )
        # Get all newly created FunctionalUses
        # bulk_create doesn't return id's if it's not pgsql
        created_funcuse = FunctionalUse.objects.filter(
            report_funcuse__in=flat_report_funcuses
        )
        # Add the new functional uses to the existing functional uses
        # After this loop all functional uses will be in funcuse_entry
        # corresponding to the form.
        for funcuse_entry, new_uses in zip(funcuses, new_funcuses):
            uses = []
            for use in new_uses:
                # Find first matching report_funcuse from newly created functional uses
                uses.append(next(i for i in created_funcuse if i.report_funcuse == use))
            uses = FunctionalUse.objects.filter(report_funcuse__in=new_uses)
            funcuse_entry.extend(uses)
        return funcuses


class CleanCompForm(forms.ModelForm):
    ExtractedComposition_id = forms.IntegerField(required=True)
    script_id = forms.IntegerField(required=True)
    weight_fraction_type_id = forms.IntegerField(required=True)

    class Meta:
        model = ExtractedComposition
        fields = ["lower_wf_analysis", "central_wf_analysis", "upper_wf_analysis"]

    def clean(self):
        super().clean()
        params = clean_dict(self.cleaned_data, ExtractedComposition, keep_nones=True)
        obj = ExtractedComposition(**params)
        obj.clean()
        # Ensure data is provided.
        central_wf_analysis = self.cleaned_data.get("central_wf_analysis")
        lower_wf_analysis = self.cleaned_data.get("lower_wf_analysis")
        upper_wf_analysis = self.cleaned_data.get("upper_wf_analysis")
        if not (central_wf_analysis or lower_wf_analysis or upper_wf_analysis):
            raise forms.ValidationError("No weight fraction data provided.")


class CleanCompFormSet(DGFormSet):
    prefix = "cleancomp"
    header_fields = ["script_id", "weight_fraction_type_id"]
    serializer = CSVReader
    form = CleanCompForm

    def __init__(self, dg, *args, **kwargs):
        self.dg = dg
        self.script_choices = [
            (str(s.pk), str(s)) for s in Script.objects.filter(script_type="DC")
        ]
        self.weight_fraction_type_choices = [
            (str(wf.pk), str(wf)) for wf in WeightFractionType.objects.all()
        ]
        super().__init__(*args, **kwargs)

    def clean(self):
        # Ensure ExtractedComposition_id's are valid
        self.cleaned_ids = [
            f.cleaned_data["ExtractedComposition_id"]
            for f in self.forms
            if "ExtractedComposition_id" in f.cleaned_data
        ]
        bad_ids = get_missing_ids(
            ExtractedComposition.objects.filter(
                extracted_text__data_document__data_group=self.dg
            ),
            self.cleaned_ids,
        )
        if bad_ids:
            bad_ids.sort()
            bad_ids_str = ", ".join(str(i) for i in bad_ids)
            raise forms.ValidationError(
                f"The following IDs do not exist in ExtractedCompositions for this data group: {bad_ids_str}"
            )
        # Ensure script ID is valid
        script_id = self.forms[0].cleaned_data.get("script_id")
        if (
            script_id
            and not Script.objects.filter(script_type="DC", pk=script_id).exists()
        ):
            raise forms.ValidationError(f"Invalid script selection.")
        # Check that weight_fraction_type is valid
        weight_fraction_type_id = self.forms[0].cleaned_data.get(
            "weight_fraction_type_id"
        )
        if (
            weight_fraction_type_id
            and not WeightFractionType.objects.filter(
                pk=weight_fraction_type_id
            ).exists()
        ):
            raise forms.ValidationError(f"Invalid weight fraction type selection.")

    def save(self):
        with transaction.atomic():
            database_chemicals = ExtractedComposition.objects.select_for_update().in_bulk(
                self.cleaned_ids
            )
            chems = []
            for form in self.forms:
                pk = form.cleaned_data["ExtractedComposition_id"]
                chem = database_chemicals[pk]
                chem.upper_wf_analysis = form.cleaned_data.get("upper_wf_analysis")
                chem.central_wf_analysis = form.cleaned_data.get("central_wf_analysis")
                chem.lower_wf_analysis = form.cleaned_data.get("lower_wf_analysis")
                chem.script_id = form.cleaned_data["script_id"]
                chem.weight_fraction_type_id = form.cleaned_data[
                    "weight_fraction_type_id"
                ]
                chem.updated_at = timezone.now()
                chems.append(chem)
            ExtractedComposition.objects.bulk_update(
                chems,
                [
                    "upper_wf_analysis",
                    "central_wf_analysis",
                    "lower_wf_analysis",
                    "script_id",
                    "weight_fraction_type_id",
                    "updated_at",
                ],
            )
        return len(self.forms)


class BulkAssignProdForm(forms.Form):
    prefix = "bulkassignprod"

    def __init__(self, dg, *args, **kwargs):
        self.dg = dg
        self.count = DataDocument.objects.filter(data_group=dg, product=None).count()
        super().__init__(*args, **kwargs)

    def save(self):
        docs = DataDocument.objects.filter(data_group=self.dg, products=None).values(
            "pk", "title", "extractedtext__prod_name"
        )
        tmp_uuid = str(uuid.uuid4())
        prods = []
        for doc in docs:
            # We temporarily set the upc to a UUID so we can locate it later.
            # This way we can then update these with "stub_{pk}". This significantly
            # reduces the number of database calls.
            upc = "%s-%d" % (tmp_uuid, doc["pk"])
            if doc["extractedtext__prod_name"]:
                title = doc["extractedtext__prod_name"]
            elif doc["title"]:
                title = doc["title"] + " stub"
            else:
                title = "unknown"
            prods.append(Product(title=title, upc=upc))
        with transaction.atomic():
            Product.objects.bulk_create(prods)
            created_prods = Product.objects.select_for_update().filter(
                upc__startswith=tmp_uuid
            )
            prod_docs = []
            for p in created_prods:
                prod_docs.append(
                    ProductDocument(product_id=p.pk, document_id=int(p.upc[37:]))
                )
            created_prods.update(upc=Concat(V("stub_"), Cast("id", CharField())))
            ProductDocument.objects.bulk_create(prod_docs)
        return self.count


class RegisterRecordsFormSet(DGFormSet):
    prefix = "register"
    serializer = CSVReader
    header_cols = [
        "filename",
        "title",
        "document_type",
        "url",
        "organization",
        "subtitle",
        "epa_reg_number",
        "pmid",
    ]

    def __init__(self, dg, *args, **kwargs):
        self.dg = dg
        self.document_types = self.dg.group_type.groups.all()
        self.form = DataDocumentCSVForm
        super().__init__(*args, **kwargs)

    def clean(self, *args, **kwargs):
        """Errors raised here are exposed in non_form_errors() and will be rendered
        before getting to any form-specific errors.
        """

        header = list(self.bulk.fieldnames)
        if header != self.header_cols:
            raise forms.ValidationError(
                f"CSV column titles should be {self.header_cols}"
            )
        if not any(self.errors):
            values = set()
            for form in self.forms:
                self._validate_doc_type_compatibility(form)
                value = form.cleaned_data.get("filename")
                if value in values:
                    raise forms.ValidationError(
                        f'Duplicate "filename" values for "{value}" are not allowed.'
                    )
                values.add(value)

    def _validate_doc_type_compatibility(self, form):
        """Validates the document_type code provided on the form is valid
        Replaces the code with the valid document_type on cleaned_data or
        raises a ValidationError if no valid document_type exists"""
        doc_type_str = form.cleaned_data.pop("document_type")
        for valid_type in self.document_types:
            if doc_type_str == valid_type.code:
                form.cleaned_data["document_type"] = valid_type
                return True

        raise forms.ValidationError(
            f"Document Type {doc_type_str} is not compatible with the {self.dg.group_type.title} Group Type."
        )

    def save(self):
        with transaction.atomic():
            new_docs = []
            now = datetime.now()
            for f in self.forms:
                f.cleaned_data["created_at"] = now
                f.cleaned_data["data_group"] = self.dg
                obj = DataDocument(**f.cleaned_data)
                new_docs.append(obj)
            DataDocument.objects.bulk_create(new_docs)
        return len(self.forms)


class DataDocumentCSVForm(forms.Form):
    filename = field_for_model(DataDocument, "filename")
    title = field_for_model(DataDocument, "title")
    document_type = forms.CharField()
    url = field_for_model(DataDocument, "url")
    organization = field_for_model(DataDocument, "organization")
    subtitle = field_for_model(DataDocument, "subtitle")
    epa_reg_number = field_for_model(DataDocument, "epa_reg_number")
    pmid = field_for_model(DataDocument, "pmid")


class FunctionalUseCSVForm(forms.Form):
    # A ModelForm does not work here because it will
    # not carry the id field
    id = forms.IntegerField(required=True)
    category_title = forms.CharField(required=True)

    class Meta:
        fields = ["id", "category_title"]


class FunctionalUseBulkCSVFormSet(DGFormSet):
    """
    Assigns extraction_script and category to existing functional use records
    """

    prefix = "functional_uses"
    serializer = CSVReader
    form = FunctionalUseCSVForm

    def __init__(self, dg, *args, **kwargs):
        self.dg = dg
        self.form = FunctionalUseCSVForm
        self.script_choices = [
            (str(s.pk), str(s)) for s in Script.objects.filter(script_type="FU")
        ]
        super().__init__(*args, **kwargs)

    def clean(self, *args, **kwargs):
        header = list(self.bulk.fieldnames)
        header_cols = ["id", "category_title"]
        if header != header_cols:
            raise forms.ValidationError(f"CSV column titles should be {header_cols}")

        for f in self.forms:
            # Convert category title string to an existing functional use category object
            category_title = f.cleaned_data.get("category_title")
            category = FunctionalUseCategory.objects.filter(
                title=category_title
            ).first()
            if not category:
                raise forms.ValidationError(
                    f"'{category_title}' is not a valid category title"
                )
            else:
                f.cleaned_data["category"] = category

    def save(self):
        updated_functional_uses = 0
        reports = []
        for f in self.forms:
            f.cleaned_data["updated_at"] = datetime.now()
            f.cleaned_data["extraction_script_id"] = self.data[
                "functional-use-script_id"
            ]
            functional_use_dict = clean_dict(f.cleaned_data, FunctionalUse)
            with transaction.atomic():
                # update the functional use record for the form
                FunctionalUse.objects.filter(pk=f.cleaned_data["id"]).update(
                    **functional_use_dict
                )
                updated_functional_uses += 1

        return updated_functional_uses, reports
