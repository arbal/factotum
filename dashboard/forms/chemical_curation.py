from django import forms
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from dashboard.utils import clean_dict
from dashboard.forms.data_group import DGFormSet
from dashboard.models.dsstox_lookup import validate_prefix, validate_blank_char
from dashboard.models import DataGroup, RawChem, DSSToxLookup
from bulkformsets import CSVReader


class DGChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        recs = obj.uncurated_count()
        return "%i: %s (%i records)" % (obj.pk, obj.name, recs)


class DataGroupSelector(forms.ModelForm):
    data_group = DGChoiceField(
        queryset=DataGroup.objects.filter(
            pk__in=RawChem.objects.filter(Q(rid=None) | Q(rid="")).values(
                "extracted_text__data_document__data_group_id"
            )
        ),
        label="Download Uncurated Chemicals by Data Group",
        required=False,
    )

    class Meta:
        model = DataGroup
        fields = ("id",)


class ChemicalCurationForm(forms.Form):

    external_id = forms.ModelChoiceField(queryset=RawChem.objects.all())
    rid = RawChem._meta.get_field("rid").formfield()
    sid = DSSToxLookup._meta.get_field("sid").formfield(required=False)
    true_chemical_name = DSSToxLookup._meta.get_field("true_chemname").formfield(
        required=False
    )
    true_cas = DSSToxLookup._meta.get_field("true_cas").formfield(required=False)

    def __init__(self, *args, **kwargs):
        super(ChemicalCurationForm, self).__init__(*args, **kwargs)
        sid_field = self.fields["sid"]
        sid_field.validators.append(validate_prefix)
        sid_field.validators.append(validate_blank_char)


class ChemicalCurationFormSet(DGFormSet):
    prefix = "curate"
    serializer = CSVReader

    def __init__(self, *args, **kwargs):
        fields = ["external_id", "rid", "sid", "true_chemical_name", "true_cas"]
        self.form = ChemicalCurationForm
        super().__init__(*args, **kwargs)

    def clean(self, *args, **kwargs):
        header = list(self.bulk.fieldnames)
        header_cols = ["external_id", "rid", "sid", "true_chemical_name", "true_cas"]
        if header != header_cols:
            raise forms.ValidationError(f"CSV column titles should be {header_cols}")

    def save(self):
        new_dsstox = []
        made_dsstox = []
        update_chems = []
        for form in self.forms:
            form.cleaned_data["true_chemname"] = form.cleaned_data["true_chemical_name"]
            dss_dict = clean_dict(form.cleaned_data, DSSToxLookup)
            # Option 1: If the sid is not set then don't attempt to match with a true chem.
            if dss_dict.get("sid") is None:
                dss = None
            # Option 2: identical DSSToxLookup already exists; just get it
            elif DSSToxLookup.objects.filter(**dss_dict).exists():
                dss = DSSToxLookup.objects.get(**dss_dict)
            else:
                # Option 3: matching DSSToxLookup exists in the db; get it and update its attributes
                if DSSToxLookup.objects.filter(sid=dss_dict["sid"]).exists():
                    dss = DSSToxLookup.objects.get(sid=dss_dict["sid"])
                    dss.true_chemname = dss_dict["true_chemname"]
                    dss.true_cas = dss_dict["true_cas"]
                    dss.updated_at = timezone.now()
                    made_dsstox.append(dss)
                # Option 4: matching DSSToxLookup exists in new_dsstox list but not yet in db; get it
                elif any(
                    dsstox for dsstox in new_dsstox if dsstox.sid == dss_dict["sid"]
                ):
                    dss = next(
                        dsstox for dsstox in new_dsstox if dsstox.sid == dss_dict["sid"]
                    )
                # Option 5: no matching DSSToxLookup exists; create it
                else:
                    dss = DSSToxLookup(**dss_dict)
                    new_dsstox.append(dss)
            chem = form.cleaned_data["external_id"]
            chem.rid = form.cleaned_data["rid"]
            chem.dsstox = dss
            chem.provisional = 0
            update_chems.append(chem)
        with transaction.atomic():
            DSSToxLookup.objects.bulk_create(new_dsstox)
            DSSToxLookup.objects.bulk_update(
                made_dsstox, ["true_chemname", "true_cas", "updated_at"]
            )
            # This is a costly way to find newly created matching DSSToxLookups
            for chem in update_chems:
                # If the dsstox model has been set but had not been saved at time of assignment
                #  fetch the dsstox from the DB
                if chem.dsstox and not chem.dsstox.pk:
                    chem.dsstox = DSSToxLookup.objects.get(sid=chem.dsstox.sid)
            RawChem.objects.bulk_update(update_chems, ["dsstox", "rid", "provisional"])
        return len(self.forms)
