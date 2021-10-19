
from dal import autocomplete

from django import forms
from bulkformsets import BaseBulkFormSet, CSVReader
from dashboard.models import Script, PUC, ProductToPUC, ExtractedHabitsAndPracticesToPUC


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


class PredictedPucCsvFormSet(BaseBulkFormSet):
    extra = 0
    can_order = False
    can_delete = False
    min_num = 1
    max_num = 50000
    absolute_max = 50000
    validate_min = True
    validate_max = True
    prefix = "predicted"
    header_cols = [
        "product_id",
        "puc_id",
    ] 
    serializer = CSVReader
    form = ProductPUCForm

    def __init__(self, *args, **kwargs):
        self.script_choices = [
            (str(s.pk), str(s)) for s in Script.objects.filter(script_type="PC")
        ]
        super().__init__(*args, **kwargs)

