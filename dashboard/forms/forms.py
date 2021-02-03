from bootstrap_datepicker_plus import DatePickerInput
from dal import autocomplete

from django import forms
from django.forms import BaseInlineFormSet

from django.utils.translation import ugettext_lazy as _

from dashboard.forms.puc_forms import BasePUCForm
from dashboard.models import (
    DataDocument,
    DataGroup,
    DataSource,
    DocumentType,
    ExtractedComposition,
    ExtractedCPCat,
    ExtractedHHDoc,
    ExtractedText,
    FunctionalUse,
    Script,
    WeightFractionType,
    QANotes,
    Product,
    ProductToPUC,
    PUCTag,
    ExtractedFunctionalUse,
    ExtractedListPresence,
    ExtractedHHRec,
    ExtractedLMDoc,
    ExtractedHabitsAndPractices,
    RawChem,
    QASummaryNote,
    DataGroupCurationWorkflow,
    CurationStep,
)
from dashboard.models.extracted_hpdoc import ExtractedHPDoc

from dashboard.utils import get_extracted_models


class DataGroupForm(forms.ModelForm):
    required_css_class = "required"  # adds to label tag
    csv = forms.FileField()

    class Meta:
        model = DataGroup
        fields = [
            "name",
            "description",
            "url",
            "group_type",
            "downloaded_by",
            "downloaded_at",
            "download_script",
            "data_source",
        ]
        widgets = {"downloaded_at": DatePickerInput()}
        labels = {"csv": _("Register Records CSV File"), "url": _("URL")}

    def __init__(self, *args, **kwargs):
        qs = Script.objects.filter(script_type="DL")
        self.user = kwargs.pop("user", None)
        super(DataGroupForm, self).__init__(*args, **kwargs)
        instance = getattr(self, "instance", None)
        if instance and instance.pk:
            self.fields.pop("csv")
        else:
            self.fields["csv"].widget.attrs.update({"accept": ".csv"})
        self.fields["download_script"].queryset = qs


class ExtractionScriptForm(forms.Form):
    required_css_class = "required"  # adds to label tag
    script_selection = forms.ModelChoiceField(
        queryset=Script.objects.filter(script_type="EX"), label="Extraction Script"
    )
    weight_fraction_type = forms.ModelChoiceField(
        queryset=WeightFractionType.objects.all(),
        label="Weight Fraction Type",
        initial="1",
    )
    extract_file = forms.FileField(label="Extracted Text CSV File")

    def __init__(self, *args, **kwargs):
        self.dg_type = kwargs.pop("dg_type", 0)
        self.user = kwargs.pop("user", None)
        super(ExtractionScriptForm, self).__init__(*args, **kwargs)
        self.fields["weight_fraction_type"].widget.attrs.update(
            {"style": "height:2.75rem; !important"}
        )
        self.fields["script_selection"].widget.attrs.update(
            {"style": "height:2.75rem; !important"}
        )
        self.fields["extract_file"].widget.attrs.update({"accept": ".csv"})
        if self.dg_type in ["FU", "CP"]:
            del self.fields["weight_fraction_type"]
        self.collapsed = True


class DataSourceForm(forms.ModelForm):
    required_css_class = "required"

    class Meta:
        model = DataSource
        fields = [
            "title",
            "url",
            "estimated_records",
            "state",
            "priority",
            "description",
        ]


class PriorityForm(forms.ModelForm):
    class Meta:
        model = DataSource
        fields = ["priority"]

    def __init__(self, *args, **kwargs):
        super(PriorityForm, self).__init__(*args, **kwargs)
        self.fields["priority"].label = ""
        self.fields["priority"].widget.attrs.update({"onchange": "form.submit();"})


class QANotesForm(forms.ModelForm):
    class Meta:
        model = QANotes
        fields = ["qa_notes"]
        widgets = {"qa_notes": forms.Textarea(attrs={"id": "qa-notes-textarea"})}
        labels = {"qa_notes": _("QA Notes (required if approving edited records)")}


class QASummaryNoteForm(forms.ModelForm):
    class Meta:
        model = QASummaryNote
        fields = ["qa_summary_note"]
        widgets = {
            "qa_summary_note": forms.Textarea(
                attrs={"id": "qa-summary-note-textarea", "rows": 4}
            )
        }


class ExtractedTextQAForm(forms.ModelForm):
    required_css_class = "required"  # adds to label tag

    class Meta:
        model = ExtractedText
        fields = ["prod_name", "data_document", "qa_checked"]


class ProductLinkForm(forms.ModelForm):
    required_css_class = "required"  # adds to label tag
    document_type = forms.ModelChoiceField(
        queryset=DocumentType.objects.all(), label="Data Document Type", required=True
    )

    return_url = forms.CharField()

    class Meta:
        model = Product
        fields = ["title", "manufacturer", "brand_name", "upc", "size", "color"]

    def __init__(self, *args, **kwargs):
        super(ProductLinkForm, self).__init__(*args, **kwargs)
        self.fields["return_url"].widget = forms.HiddenInput()


class ProductForm(forms.ModelForm):
    required_css_class = "required"  # adds to label tag

    class Meta:
        model = Product
        fields = [
            "title",
            "manufacturer",
            "brand_name",
            "size",
            "color",
            "model_number",
            "short_description",
            "long_description",
            "epa_reg_number",
            "url",
        ]


class ProductViewForm(ProductForm):
    class Meta(ProductForm.Meta):
        exclude = ("title", "long_description")

    def __init__(self, *args, **kwargs):
        super(ProductForm, self).__init__(*args, **kwargs)
        for f in self.fields:
            self.fields[f].disabled = True


class BulkProductPUCForm(BasePUCForm):
    id_pks = forms.CharField(
        label="Product Titles", widget=forms.HiddenInput(), required=True
    )

    class Meta:
        model = ProductToPUC
        fields = ["puc", "id_pks"]


class BulkProductTagForm(forms.ModelForm):
    required_css_class = "required"  # adds to label tag
    tag = forms.ModelChoiceField(queryset=PUCTag.objects.none(), label="Attribute")
    id_pks = forms.CharField(label="Product Titles", widget=forms.HiddenInput())

    class Meta:
        model = ProductToPUC
        fields = ["tag", "id_pks"]

    def __init__(self, *args, **kwargs):
        super(BulkProductTagForm, self).__init__(*args, **kwargs)
        lbl = "Select Attribute to Assign to Selected Products"
        self.fields["tag"].label = lbl


class ExtractedTextForm(forms.ModelForm):
    class Meta:
        model = ExtractedText
        fields = ["prod_name", "doc_date", "rev_num"]

        widgets = {
            "data_document": forms.HiddenInput(),
            "extraction_script": forms.HiddenInput(),
        }


class ExtractedTextHPForm(ExtractedTextForm):
    class Meta:
        model = ExtractedHPDoc
        fields = ["doc_date", "rev_num"]


class ExtractedTextFUForm(ExtractedTextForm):
    class Meta:
        model = ExtractedText
        fields = ["doc_date", "rev_num"]


class ExtractedCPCatForm(ExtractedTextForm):
    class Meta:
        model = ExtractedCPCat
        fields = ["doc_date"]


class ExtractedHHDocForm(ExtractedTextForm):
    class Meta:
        model = ExtractedHHDoc
        fields = [
            "hhe_report_number",
            "study_location",
            "naics_code",
            "sampling_date",
            "population_gender",
            "population_age",
            "population_other",
            "occupation",
            "facility",
        ]


class ExtractedLMDocForm(ExtractedTextForm):
    class Meta:
        model = ExtractedLMDoc
        fields = ["doc_date", "study_type", "media"]

        widgets = {
            "study_type": forms.Select(attrs={"style": "width:320px"}),
            "media": forms.Textarea(attrs={"rows": 4, "cols": 25}),
        }


class ExtractedHHDocEditForm(ExtractedHHDocForm):
    class Meta(ExtractedHHDocForm.Meta):
        fields = ExtractedHHDocForm.Meta.fields + ["doc_date"]


class DocumentTypeForm(forms.ModelForm):
    class Meta:
        model = DataDocument
        fields = ["document_type"]

    def __init__(self, *args, **kwargs):
        super(DocumentTypeForm, self).__init__(*args, **kwargs)
        self.fields["document_type"].label = ""
        self.fields["document_type"].help_text = None
        self.fields["document_type"].widget.attrs.update({"onchange": "form.submit();"})


class RawChemicalSubclassFormSet(BaseInlineFormSet):
    """ The formset used for all the subclasses of RawChemical,
    since it includes the Functional Use records as a nested formset """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def add_fields(self, form, index):
        # the super class creates its fields
        super(RawChemicalSubclassFormSet, self).add_fields(form, index)
        # add the grandchild formset as the 'functional_uses' property,
        # only if the form is bound to an instance
        if form.instance.pk is not None:
            FunctionalUseFormset = forms.inlineformset_factory(
                RawChem,
                FunctionalUse,
                fields=("id", "category", "report_funcuse", "extraction_script"),
                extra=0,
                # widgets={"id": forms.HiddenInput()},
            )
            form.functional_uses = FunctionalUseFormset(
                instance=form.instance,
                data=form.data if self.is_bound else None,
                prefix="%s-%s"
                % (form.prefix, FunctionalUseFormset.get_default_prefix()),
            )

    def is_valid(self):
        result = super(RawChemicalSubclassFormSet, self).is_valid()
        if self.is_bound:
            for form in self.forms:
                if hasattr(form, "functional_uses"):
                    result = result and form.functional_uses.is_valid()

        return result

    def has_changed(self):
        result = super(RawChemicalSubclassFormSet, self).has_changed()
        if self.is_bound:
            for form in self.forms:
                if hasattr(form, "functional_uses"):
                    result = result or form.functional_uses.has_changed()

        return result

    def save(self, commit=True):
        for form in self:
            if hasattr(form, "functional_uses"):
                for fu in form.functional_uses:
                    fu.save(commit=commit)
        result = super(RawChemicalSubclassFormSet, self).save(commit=commit)
        return result


class ExtractedCompositionForm(forms.ModelForm):
    class Meta:
        model = ExtractedComposition
        fields = [
            "raw_chem_name",
            "raw_cas",
            "raw_min_comp",
            "raw_central_comp",
            "raw_max_comp",
            "unit_type",
            "ingredient_rank",
            "weight_fraction_type",
            "component",
        ]


class ExtractedLMChemicalForm(forms.ModelForm):
    class Meta:
        model = RawChem
        fields = ["raw_chem_name", "raw_cas", "chem_detected_flag"]


class ExtractedFunctionalUseForm(forms.ModelForm):
    class Meta:
        model = ExtractedFunctionalUse
        fields = ["raw_chem_name", "raw_cas"]


class ExtractedHabitsAndPracticesForm(forms.ModelForm):
    required_css_class = "required"  # adds to label tag

    class Meta:
        model = ExtractedHabitsAndPractices
        fields = ["product_surveyed", "data_type", "notes", "PUCs"]
        widgets = {
            "PUCs": autocomplete.ModelSelect2Multiple(
                attrs={"data-minimum-input-length": 3, "class": "w-100 h-100"}
            )
        }


class ExtractedListPresenceForm(forms.ModelForm):
    class Meta:
        model = ExtractedListPresence
        fields = ["raw_chem_name", "raw_cas", "component", "chem_detected_flag"]


class ExtractedHHRecForm(forms.ModelForm):
    class Meta:
        model = ExtractedHHRec
        fields = [
            "raw_chem_name",
            "raw_cas",
            "media",
            "num_measure",
            "num_nondetect",
            "sampling_method",
            "analytical_method",
        ]


def create_detail_formset(document, extra=1, can_delete=False, exclude=[], hidden=[]):
    """Returns the pair of formsets that will be needed based on group_type.
    .                       ('CO'),('CP'),('FU'),('HP'),('HH'),('LM')
    Parameters
        ----------
        document : DataDocument
            The parent DataDocument
        extra : integer
            How many empty forms should be created for new records
        can_delete : boolean
            whether a delete checkbox is included
        exclude : list
            which fields to leave out of the form
        hidden : list
            which fields to make hidden on the form
    .

    """
    group_type = document.data_group.type
    parent, child = get_extracted_models(group_type)
    extracted = hasattr(document, "extractedtext")

    def make_formset(
        parent_model,
        model,
        formset=BaseInlineFormSet,
        form=forms.ModelForm,
        exclude=exclude,
        hidden=hidden,
    ):
        formset_fields = model.detail_fields()
        if exclude:
            formset_fields = [
                in_field for in_field in formset_fields if in_field not in exclude
            ]
        # set fields to hidden if so specified
        widgets = dict(
            [
                (in_field, forms.HiddenInput())
                for in_field in formset_fields
                if in_field in hidden
            ]
        )
        return forms.inlineformset_factory(
            parent_model=parent_model,
            model=model,
            fields=formset_fields,
            formset=formset,  # this specifies a custom formset
            form=form,
            extra=extra,
            can_delete=can_delete,
            widgets=widgets,
            fk_name="extracted_text",
        )

    def one():  # for chemicals or unknown
        ChemicalFormSet = make_formset(
            parent_model=parent,
            model=child,
            formset=RawChemicalSubclassFormSet,
            form=ExtractedCompositionForm,
        )
        return (ExtractedTextForm, ChemicalFormSet)

    def two():  # for functional_use
        FunctionalUseFormSet = make_formset(
            parent_model=parent, model=child, formset=RawChemicalSubclassFormSet
        )
        return (ExtractedTextFUForm, FunctionalUseFormSet)

    def three():  # for habits_and_practices
        HnPFormSet = make_formset(parent, child)
        return (ExtractedTextHPForm, HnPFormSet)

    def four():  # for extracted_list_presence
        ListPresenceFormSet = make_formset(
            parent_model=parent, model=child, formset=RawChemicalSubclassFormSet
        )
        return (ExtractedCPCatForm, ListPresenceFormSet)

    def five():  # for extracted_hh_rec
        HHFormSet = make_formset(parent, child)
        ParentForm = ExtractedHHDocForm if extracted else ExtractedHHDocEditForm
        return (ParentForm, HHFormSet)

    def six():  # for extracted_lm_doc
        LMDocFormSet = make_formset(parent, child)
        return (ExtractedLMDocForm, LMDocFormSet)

    dg_types = {
        "CO": one,
        "UN": one,
        "FU": two,
        "HP": three,
        "CP": four,
        "HH": five,
        "LM": six,
    }
    func = dg_types.get(group_type, lambda: None)
    return func()


class DataDocumentForm(forms.ModelForm):
    required_css_class = "required"

    class Meta:
        model = DataDocument
        fields = [
            "title",
            "subtitle",
            "document_type",
            "note",
            "url",
            "raw_category",
            "organization",
            "epa_reg_number",
            "pmid",
        ]
        widgets = {
            "pmid": forms.TextInput(
                attrs={
                    "type": "number",
                    "min": "0",
                    "step": "1",
                    "style": "-moz-appearance: textfield",
                }
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["raw_category"].label = "Source category"
        self.fields["document_type"].queryset = DocumentType.objects.compatible(
            self.instance
        )
        if self.instance.data_group.type not in ["LM", "HP", "LP"]:
            del self.fields["pmid"]


class DataGroupWorkflowForm(forms.ModelForm):
    class Meta:
        model = DataGroup
        fields = ["workflow_complete"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        curation_steps = CurationStep.objects.all()
        for step in curation_steps:
            current_status = DataGroupCurationWorkflow.objects.filter(
                data_group_id=self.instance.id, curation_step_id=step.id
            ).first()
            field_name = "step_%d" % (step.id,)
            self.fields[field_name] = forms.ChoiceField(
                required=False,
                choices=DataGroupCurationWorkflow.STEP_STATUS_CHOICES,
                initial=current_status.step_status
                if current_status is not None
                else "I",
                label=step.name,
            )
        # move this field to bottom
        wc = self.fields.pop("workflow_complete")
        self.fields["workflow_complete"] = wc
        self.fields["workflow_complete"].label = "Workflow Complete"

    def save(self):
        datagroup = self.instance
        datagroup.workflow_complete = self.cleaned_data["workflow_complete"]
        datagroup.save()
        # save/create each step
        curation_steps = CurationStep.objects.all()
        for step in curation_steps:
            field_name = "step_%d" % (step.id,)
            current_status = DataGroupCurationWorkflow.objects.filter(
                data_group_id=self.instance.id, curation_step_id=step.id
            ).first()
            if current_status is None:
                current_status = DataGroupCurationWorkflow(
                    data_group=self.instance, curation_step=step
                )
            current_status.step_status = self.cleaned_data[field_name]
            current_status.save()
