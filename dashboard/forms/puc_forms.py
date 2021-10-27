from dal import autocomplete

from django import forms
from bulkformsets import BaseBulkFormSet, CSVReader
from dashboard.models import Script, PUC, ProductToPUC, ExtractedHabitsAndPracticesToPUC
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
    puc_assigned_script_id = forms.IntegerField(required=False)
    classification_confidence = RoundingDecimalFormField(max_digits = 5, decimal_places=3, required=False)


    class Meta:
        model = ProductToPUC
        fields = ["product", "puc", "classification_confidence"]


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def clean(self, *args, **kwargs):
        if self.script_id:
            self.script = Script.objects.get(pk=self.script_id)

        cleaned_data = super().clean()
        header = list(self.bulk.fieldnames)
        header_cols = ["product", "puc", "classification_confidence"]
        if header != header_cols:
            raise forms.ValidationError(f"CSV column titles should be {header_cols}")
        return cleaned_data

    def save(self):
        created_recs = 0
        updated_recs = 0
        for form in self.forms:
            # if the product has already been assigned a PUC via the AU method,
            # update the existing record with the new PUC
            p2p, created = ProductToPUC.objects.update_or_create(
                classification_method_id="AU",
                product=form.cleaned_data["product"],
                defaults={
                    "classification_method_id": "AU",
                    "puc": form.cleaned_data["puc"],
                    "puc_assigned_script": self.script,
                    "puc_assigned_usr": self.user,
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
