from django.db import models
from .common_info import CommonInfo
from django.core.exceptions import ValidationError
from .extracted_text import ExtractedText


class ExtractedFunctionalUse(CommonInfo):
    extracted_text = models.ForeignKey(ExtractedText, on_delete=models.CASCADE,
                                    related_name='uses')
    raw_cas = models.CharField("Raw CAS", max_length=50, null=True, blank=True)
    raw_chem_name = models.CharField("Raw chemical name", max_length=500,
                                  null=True, blank=True)
    report_funcuse = models.CharField("Reported functional use",
                                        max_length=100, null=True, blank=True)

    def __str__(self):
        return self.raw_chem_name
