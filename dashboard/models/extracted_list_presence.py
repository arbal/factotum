from django.db import models

from dashboard.models import CommonInfo
from .raw_chem import RawChem

class ExtractedListPresence(CommonInfo, RawChem):

    raw_cas_old = models.CharField("Raw CAS", max_length=100,
                                        null=True, blank=True)
    raw_chem_name_old = models.CharField("Raw chemical name", max_length=500,
                                        null=True, blank=True)
    qa_flag = models.BooleanField(default=False)

    @classmethod
    def detail_fields(cls):
        return ['raw_cas','raw_chem_name']

    def __str__(self):
        return str(self.raw_chem_name) if self.raw_chem_name else ''

    def get_datadocument_url(self):
        return self.extracted_cpcat.data_document.get_absolute_url()

    def get_extractedtext(self):
        return self.extracted_cpcat.extractedtext_ptr
    
    @property
    def data_document(self):
        return self.extracted_text.data_document
