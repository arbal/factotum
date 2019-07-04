from model_utils import FieldTracker
from model_utils.managers import InheritanceManager
from django.db import models
from django.apps import apps
from django.db.models.signals import pre_save


class RawChem(models.Model):
    extracted_text = models.ForeignKey('ExtractedText', related_name = 'rawchem',
        on_delete=models.CASCADE, null=False, blank = False)

    raw_cas = models.CharField("Raw CAS", max_length=100, null=True, blank=True)
    raw_chem_name = models.CharField("Raw chemical name", max_length=1300,
                                                        null=True, blank=True)
    temp_id = models.IntegerField(default=0, null=True, blank=True)
    temp_obj_name = models.CharField(max_length=255, null=True, blank=True)

    rid = models.CharField(max_length=50, null=True, blank=True)

    dsstox = models.ForeignKey('DSSToxLookup', related_name = 'curated_chemical', on_delete=models.PROTECT,
                                                    null=True, blank=True)

    objects = InheritanceManager()

    tracker = FieldTracker()

    def __str__(self):
        return str(self.raw_chem_name) if self.raw_chem_name else ''

    @property
    def sid(self):
        '''If there is no DSSToxLookup record via the 
        curated_chemical relationship, it evaluates to boolean False '''
        try:
            return self.curated_chemical.sid
        except AttributeError:
            return False

    @property
    def data_group_id(self):
        return str(self.extracted_text.data_document.data_group_id)

    def get_data_document(self):
        '''Find the child object by trying each of the classes, then return the 
            datadocument id from it
            NOTE: this will be obsolete once we move the data_document 
            foreign key into RawChem in ticket 654
         '''
        id=self.id
        try:
            return apps.get_model('dashboard.ExtractedChemical').objects.get(rawchem_ptr=id).data_document
        except apps.get_model('dashboard.ExtractedChemical').DoesNotExist:
            try: 
                return apps.get_model('dashboard.ExtractedFunctionalUse').objects.get(rawchem_ptr=id).data_document
            except apps.get_model('dashboard.ExtractedFunctionalUse').DoesNotExist:
                try: 
                    return apps.get_model('dashboard.ExtractedListPresence').objects.get(rawchem_ptr=id).data_document
                except apps.get_model('dashboard.ExtractedListPresence').DoesNotExist: 
                    return False

    def clean(self):
        def whitespace(fld):
            if fld:
                return fld.startswith(' ') or fld.endswith(' ')
            else:
                return False

        if whitespace(self.raw_cas):
            self.raw_cas = self.raw_cas.strip()
        if whitespace(self.raw_chem_name):
            self.raw_chem_name = self.raw_chem_name.strip()

    @property
    def true_cas(self):
        if hasattr(self, 'dsstox') and self.dsstox is not None:
            return self.dsstox.true_cas
        else:
            return None

    @property
    def true_chemname(self):
        if hasattr(self, 'dsstox') and self.dsstox is not None:
            return self.dsstox.true_chemname
        else:
            return None

    @property
    def rendered_chemname(self):
        if hasattr(self, 'dsstox') and self.dsstox is not None:
            return self.dsstox.true_chemname
        else:
            return self.raw_chem_name

    @property
    def rendered_cas(self):
        if hasattr(self, 'dsstox') and self.dsstox is not None:
            return self.dsstox.true_cas
        else:
            return self.raw_cas
