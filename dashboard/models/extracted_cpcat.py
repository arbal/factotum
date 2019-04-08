from django.db import models
from .extracted_text import ExtractedText


class ExtractedCPCat(ExtractedText):
    cat_code = models.CharField("Cat Code", max_length=100,
                                        null=True, blank=True)
    description_cpcat = models.CharField("Description CPCat", max_length=200,
                                        null=True, blank=True)
    cpcat_code = models.CharField("CPCat Code", max_length=50,
                                        null=True, blank=True)
    cpcat_sourcetype = models.CharField("CPCat SourceType", max_length=50,
                                        null=True, blank=True)

    def __str__(self):
        return str(self.prod_name)

    @property
    def qa_begun(self):
        return self.rawchem.select_subclasses().filter(extractedlistpresence__qa_flag=True).count() > 0