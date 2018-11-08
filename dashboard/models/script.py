from django.db import models
from django.urls import reverse
from django.core.validators import URLValidator

from .common_info import CommonInfo
from .data_document import DataDocument


class Script(CommonInfo):

    TYPE_CHOICES = (('DL', 'download'),
                    ('EX', 'extraction'),
                    ('PC', 'product categorization'))

    # Specify the share of a script's ExtractedText objects that must be
    # approved in order for the script's QA sat
    QA_COMPLETE_PERCENTAGE = 0.2


    title = models.CharField(max_length=50)
    url = models.CharField(max_length  = 100,
                            null       = True,
                            blank      = True,
                            validators = [URLValidator()])
    qa_begun = models.BooleanField(default=False)
    script_type = models.CharField( max_length = 2,
                                    choices    = TYPE_CHOICES,
                                    blank      = False,
                                    default    = 'EX')

    def __str__(self):
        return str(self.title)

    def get_absolute_url(self):
        return reverse('extraction_script_edit', kwargs={'pk': self.pk})

    def get_datadocument_count(self):
        return DataDocument.objects.filter(
                extractedtext__extraction_script=self.pk).count()

    def get_qa_complete_extractedtext_count(self):
        return DataDocument.objects.filter(extractedtext__qa_checked=True,
                            extractedtext__extraction_script=self.pk).count()

    def get_pct_checked(self):
        count = self.get_datadocument_count()
        pct = (0 if count == 0 else (
                      self.get_qa_complete_extractedtext_count() / count * 100))
        return "{0:.0f}%".format(pct)

    def get_pct_checked_numeric(self):
        count = self.get_datadocument_count()
        pct = (0 if count == 0 else (
                      self.get_qa_complete_extractedtext_count() / count * 100))
        return pct

    def qa_button_text(self):
        return "Begin QA" if not self.qa_begun else "Continue QA"

    def get_qa_status(self):
        """
        Compare the derived percent checked against the threshold constant
        Return true when the percent checked is above the threshold
        """
        return self.get_pct_checked_numeric() >= QA_COMPLETE_PERCENTAGE * 100
