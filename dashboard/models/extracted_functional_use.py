from django.db import models
from .common_info import CommonInfo
from django.core.exceptions import ValidationError
from .extracted_text import ExtractedText
from .raw_chem import RawChem

class ExtractedFunctionalUse(CommonInfo, RawChem):

    raw_cas_old = models.CharField("Raw CAS", max_length=50, null=True, blank=True)
    raw_chem_name_old = models.CharField("Raw chemical name", max_length=500,
                                  null=True, blank=True)
    report_funcuse = models.CharField("Reported functional use",
                                        max_length=100, null=True, blank=True)

    def __str__(self):
        return self.raw_chem_name

    @classmethod
    def detail_fields(cls):
        return ['extracted_text','raw_cas','raw_chem_name','report_funcuse']

    def get_extractedtext(self):
        return self.extracted_text

    @property
    def data_document(self):
        return self.extracted_text.data_document
