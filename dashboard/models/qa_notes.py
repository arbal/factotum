from django.db import models
from .common_info import CommonInfo
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from dashboard.models import ExtractedText


class QANotes(CommonInfo):
    extracted_text = models.ForeignKey(ExtractedText, on_delete=models.CASCADE)
    qa_notes = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return 'Notes for {}'.format(self.extracted_text)

    def clean(self):

        # print('------inside the QANotes model clean')
        # print(self.extracted_text.qa_edited)

        if self.extracted_text.qa_edited and self.qa_notes is None:
            raise ValidationError(_('qa_notes needs to be populated if you edited the data'))
