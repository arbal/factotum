import sys
import uuid
import zipfile

from django import forms
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import transaction
from django.db.models import CharField, Value as V
from django.db.models.functions import Cast, Concat

from bulkformsets import BaseBulkFormSet, CSVReader
from dashboard.models import DataDocument, Ingredient, Product, ProductDocument, Script
from dashboard.utils import clean_dict, get_extracted_models, get_form_for_models


class DGFormSet(BaseBulkFormSet):
    extra = 0
    can_order = False
    can_delete = False
    min_num = 1
    max_num = sys.maxsize
    absolute_max = sys.maxsize
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
        uploaded_filenames = set(
            f.name for f in self.files.getlist("%s-documents" % self.prefix)
        )
        self.datadocuments = DataDocument.objects.filter(
            data_group=self.dg, filename__in=uploaded_filenames
        )
        if not self.datadocuments.exists():
            raise forms.ValidationError(
                "There are no matching filenames in the directory selected."
            )

    def save(self):
        store = settings.MEDIA_URL + str(self.dg.fs_id)
        fs = FileSystemStorage(store + "/pdf")
        upd_list = []
        doc_dict = {d.name: d for d in self.files.getlist("%s-documents" % self.prefix)}
        # TODO: we'll have dangling files if there is a failure in here
        with zipfile.ZipFile(self.dg.zip_file, "a", zipfile.ZIP_DEFLATED) as zf:
            for datadocument in self.datadocuments:
                docfile = doc_dict[datadocument.filename]
                afn = datadocument.get_abstract_filename()
                fs.save(afn, docfile)
                zf.write(store + "/pdf/" + afn, afn)
                datadocument.matched = True
                upd_list.append(datadocument)
        DataDocument.objects.bulk_update(self.datadocuments, ["matched"])
        return self.datadocuments.count()


class ExtractFileFormSet(DGFormSet):
    prefix = "extfile"
    header_fields = ["weight_fraction_type", "extraction_script"]
    serializer = CSVReader

    def __init__(self, dg, *args, **kwargs):
        # We seem to be doing nothing with DataDocument.filename even though it's
        # being collected. It will still be validated against though.
        self.dg = dg
        Parent, Child = get_extracted_models(dg.type)
        fields = dg.get_extracted_template_fieldnames() + self.header_fields
        self.form = get_form_for_models(
            Parent,
            Child,
            DataDocument,
            fields=fields,
            translations={"data_document_filename": "filename"},
            skip_missing=True,
        )
        super().__init__(*args, **kwargs)

    def clean(self):
        Parent, Child = get_extracted_models(self.dg.type)
        if hasattr(Parent, "cat_code"):
            oto_field = "cat_code"
        elif hasattr(Parent, "prod_name"):
            oto_field = "prod_name"
        else:
            return
        invalid_oto = []
        # First check against values in the database
        for p in Parent.objects.filter(
            pk__in=(f.cleaned_data["data_document_id"].pk for f in self.forms)
        ):
            for f in self.forms:
                if f.cleaned_data["data_document_id"].pk == p.pk and f.cleaned_data[
                    oto_field
                ] != getattr(p, oto_field):
                    invalid_oto.append((p.pk, getattr(p, oto_field)))
        # Now check against values within the form
        for i, f1 in enumerate(self.forms):
            for f2 in self.forms[i:]:
                if (
                    f1.cleaned_data["data_document_id"].pk
                    == f2.cleaned_data["data_document_id"].pk
                    and f1.cleaned_data[oto_field] != f2.cleaned_data[oto_field]
                ):
                    invalid_oto.append(
                        (
                            f1.cleaned_data["data_document_id"],
                            f1.cleaned_data[oto_field],
                        )
                    )

        if invalid_oto:
            err_str = (
                'The following "data_document_id"s got unexpected "%s"s (must be 1:1): '
                % oto_field
            )
            err_str += ", ".join(
                '%d (expected "%s" to be "%s")' % (o[0].pk, oto_field, o[1])
                for o in invalid_oto
            )
            raise forms.ValidationError(err_str)

    def save(self):
        Parent, Child = get_extracted_models(self.dg.type)
        raw_cat_map = {
            f.cleaned_data["data_document_id"].pk: f.cleaned_data["raw_category"]
            for f in self.forms
        }
        parent_collected_ids = set()
        with transaction.atomic():
            # DataDocument update
            docs = []
            for obj in DataDocument.objects.select_for_update().filter(
                pk__in=(f.cleaned_data["data_document_id"].pk for f in self.forms)
            ):
                obj.raw_category = raw_cat_map[obj.pk]
                docs.append(obj)
            DataDocument.objects.bulk_update(docs, ["raw_category"])
            # There's no real good way to do bulk creates/updates for inherited models
            # Parent update or create
            for f in self.forms:
                if f.cleaned_data["data_document_id"].pk not in parent_collected_ids:
                    params = clean_dict(f.cleaned_data, Parent)
                    params["data_document_id"] = f.cleaned_data["data_document_id"].pk
                    try:
                        obj = Parent.objects.get(
                            data_document_id=params["data_document_id"]
                        )
                        params.pop("data_document_id")
                        for key, value in params.items():
                            setattr(obj, key, value)
                        obj.save()
                    except Parent.DoesNotExist:
                        obj = Parent(**params)
                        obj.save()
                    parent_collected_ids.add(params["data_document_id"])
            # Child create
            for f in self.forms:
                params = clean_dict(f.cleaned_data, Child)
                params["extracted_text_id"] = f.cleaned_data["data_document_id"].pk
                Child.objects.create(**params)
            # Store CSV
            fs = FileSystemStorage(settings.MEDIA_URL + str(self.dg.fs_id))
            fs.save(
                str(self.dg) + "_extracted.csv",
                self.files["extfile-bulkformsetfileupload"],
            )
        return len(self.forms)


class CleanCompFormSet(DGFormSet):
    prefix = "cleancomp"
    header_fields = ["script"]
    serializer = CSVReader

    def __init__(self, dg, *args, **kwargs):
        self.dg = dg
        fields = dg.get_clean_comp_data_fieldnames() + self.header_fields
        self.form = get_form_for_models(
            Ingredient,
            fields=fields,
            translations={"id": "rawchem_ptr"},
            required=fields,
            formfieldkwargs={
                "script": {"queryset": Script.objects.filter(script_type="DC")}
            },
        )
        super().__init__(*args, **kwargs)

    def save(self):
        rawchem_ptr_map = {
            f.cleaned_data["id"].pk: clean_dict(
                f.cleaned_data, Ingredient, translations={"id": "rawchem_ptr"}
            )
            for f in self.forms
        }
        # The upd_fieldnames are the fields we are upating, so we'll
        # remove the id
        upd_fieldnames = set(self.dg.get_clean_comp_data_fieldnames())
        upd_fieldnames.remove("id")
        with transaction.atomic():
            # Updates
            ing_upd = [
                obj
                for obj in Ingredient.objects.select_for_update().filter(
                    rawchem_ptr_id__in=rawchem_ptr_map.keys()
                )
            ]
            for obj in ing_upd:
                params = rawchem_ptr_map[obj.pk]
                for key, value in params.items():
                    if key in upd_fieldnames:
                        setattr(obj, key, value)
            Ingredient.objects.bulk_update(ing_upd, list(upd_fieldnames))
            # Creates
            upd_rawchem_ptr = set(i.rawchem_ptr for i in ing_upd)
            ing_new = []
            for f in self.forms:
                rawchem_ptr = f.cleaned_data["id"].pk
                if rawchem_ptr not in upd_rawchem_ptr:
                    obj = Ingredient(**rawchem_ptr_map[rawchem_ptr])
                    ing_new.append(obj)
            Ingredient.objects.bulk_create(ing_new)
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
