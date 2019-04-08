from django.db import models
from .common_info import CommonInfo
from .extracted_text import ExtractedText
from .script import Script


class QAGroup(CommonInfo):
    extraction_script = models.ForeignKey(Script,
                                    on_delete=models.CASCADE,
                                    related_name='qa_group',
                                    blank=False, null=False,
                                    limit_choices_to={'script_type': 'EX'}, )
    qa_complete = models.BooleanField(default=False)

    def __str__(self):
        return str(self.extraction_script) + '_' + str(self.pk)

    def get_approved_doc_count(self):
        return ExtractedText.objects.filter(qa_group=self,
                                            qa_checked=True).count()
