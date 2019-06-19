from django import forms

from dashboard.models import DataGroup, RawChem

class DGChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        recs = RawChem.objects.filter(dsstox__isnull=True).filter(extracted_text__data_document__data_group=obj).count()
        return "%i: %s (%i records)" % (obj.pk, obj.name, recs)

class DataGroupSelector(forms.ModelForm):
    data_group = DGChoiceField(
        queryset=DataGroup.objects.all(),
        label="Download uncurated chemicals for a Data Group",
        required=False)

    class Meta:
        model = DataGroup
        fields = ('id',)



