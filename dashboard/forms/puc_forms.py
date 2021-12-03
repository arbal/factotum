from dal import autocomplete

from django import forms
from bulkformsets import BaseBulkFormSet, CSVReader
from dashboard.models import Script, PUC, ProductToPUC, ExtractedHabitsAndPracticesToPUC
from django.contrib.auth.models import User
from celery_formtask.forms import FormTaskMixin
from decimal import Decimal


def round_decimal(value, places):
    if value is not None:
        # see https://docs.python.org/2/library/decimal.html#decimal.Decimal.quantize for options
        return value.quantize(Decimal(10) ** -places)
    return value


class BasePUCForm(forms.ModelForm):
    puc = forms.ModelChoiceField(
        queryset=PUC.objects.all(),
        label="Category",
        widget=autocomplete.ModelSelect2(
            url="puc-autocomplete",
            attrs={"data-minimum-input-length": 3, "class": "ml-2"},
        ),
    )


class ProductPUCForm(BasePUCForm):
    class Meta:
        model = ProductToPUC
        fields = ["puc"]


class HabitsPUCForm(BasePUCForm):
    class Meta:
        model = ExtractedHabitsAndPracticesToPUC
        fields = ["puc"]


class BulkPUCForm(BasePUCForm):
    class Meta:
        model = ProductToPUC
        fields = ["puc"]

    def __init__(self, *args, **kwargs):
        super(BulkPUCForm, self).__init__(*args, **kwargs)
        lbl = "Select PUC"
        self.fields["puc"].label = lbl
        self.fields["puc"].widget.attrs["onchange"] = "form.submit();"


class RoundingDecimalFormField(forms.DecimalField):
    def to_python(self, value):
        value = super(RoundingDecimalFormField, self).to_python(value)
        return round_decimal(value, self.decimal_places)


class ProductToPucForm(forms.ModelForm):
    puc_assigned_script = forms.ModelChoiceField(
        Script.objects.filter(script_type="PC"),
        widget=forms.HiddenInput(),
        required=False,
    )
    puc_assigned_usr = forms.ModelChoiceField(
        User.objects.all(), widget=forms.HiddenInput(), required=False
    )
    classification_confidence = RoundingDecimalFormField(
        max_digits=5, decimal_places=3, required=False
    )

    class Meta:
        model = ProductToPUC
        fields = [
            "product",
            "puc",
            "classification_confidence",
            "puc_assigned_script",
            "puc_assigned_usr",
        ]

    def __init__(
        self, puc_assigned_script=None, puc_assigned_usr=None, *args, **kwargs
    ):
        puc_assigned_script = kwargs.pop("puc_assigned_script", None)
        puc_assigned_usr = kwargs.pop("puc_assigned_usr", None)
        super(ProductToPucForm, self).__init__(*args, **kwargs)


class PredictedPucCsvFormSet(FormTaskMixin, BaseBulkFormSet):
    extra = 0
    can_order = False
    can_delete = False
    min_num = 1
    max_num = 50000
    absolute_max = 50000
    validate_min = True
    validate_max = True
    prefix = "predicted"
    header_cols = ["product", "puc", "classification_confidence"]
    serializer = CSVReader
    form = ProductToPucForm

    def clean(self, *args, **kwargs):
        self.set_progress(
            current=1, total=len(self.forms), description="Validating predicted PUCs"
        )
        cleaned_data = super().clean()

        header = list(self.bulk.fieldnames)
        header_cols = ["product", "puc", "classification_confidence"]
        if header != header_cols:
            raise forms.ValidationError(f"CSV column titles should be {header_cols}")
        return cleaned_data

    def save(self):
        # these kwargs are not working in the subform init method
        puc_assigned_script = self.form_kwargs.pop("puc_assigned_script", None)
        puc_assigned_usr = self.form_kwargs.pop("puc_assigned_usr", None)
        created_recs = 0
        updated_recs = 0
        self.set_progress(
            current=2, total=len(self.forms), description="Saving predicted PUCs"
        )
        for form in self.forms:
            # if the product has already been assigned a PUC via the AU method,
            # update the existing record with the new PUC
            p2p, created = ProductToPUC.objects.update_or_create(
                classification_method_id="AU",
                product=form.cleaned_data["product"],
                defaults={
                    "classification_method_id": "AU",
                    "puc": form.cleaned_data["puc"],
                    "puc_assigned_script_id": puc_assigned_script,
                    "puc_assigned_usr_id": puc_assigned_usr,
                    "classification_confidence": form.cleaned_data[
                        "classification_confidence"
                    ],
                },
            )
            p2p.update_uber_puc()

            if created:
                created_recs += 1
            else:
                updated_recs += 1

        return created_recs, updated_recs
