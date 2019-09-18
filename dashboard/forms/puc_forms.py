from dal import autocomplete

from django import forms

from dashboard.models import PUC, ProductToPUC, ExtractedHabitsAndPracticesToPUC


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
