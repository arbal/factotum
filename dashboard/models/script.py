import math
from random import shuffle

from django.db import models
from django.urls import reverse
from django.core.validators import (URLValidator, MaxValueValidator, 
                                                    MinValueValidator)

from .common_info import CommonInfo
from .data_document import DataDocument


class Script(CommonInfo):

    TYPE_CHOICES = (('DL', 'download'),
                    ('EX', 'extraction'),
                    ('PC', 'product categorization'),
                    ('DC', 'data cleaning'))

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
    confidence = models.PositiveSmallIntegerField('Confidence', blank=True,
                                                validators=[
                                                        MaxValueValidator(100),
                                                        MinValueValidator(1)],
                                                                default=1)

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
        if self.get_qa_status():
            return "QA Complete" 
        elif self.qa_begun:
            return "Continue QA"
        else:
            return "Begin QA"

    def get_qa_status(self):
        """
        Compare the derived percent checked against the threshold constant
        Return true when the percent checked is above the threshold
        """
        return self.get_pct_checked_numeric() >= self.QA_COMPLETE_PERCENTAGE * 100

    def create_qa_group(self, force_doc_id=None):
        """
        Creates a QA Group for the specified Script object;
        Use all the related ExtractedText records or, if there are more than 100,
        select 20% of them. 
        """
        from .qa_group import QAGroup
        from .extracted_text import ExtractedText
        es = self
        # Handle cases where a QA group already exists for the script
        if QAGroup.objects.filter(extraction_script = es).count() == 1:
            # This is a valid state
            return QAGroup.objects.get(extraction_script = es)
        elif QAGroup.objects.filter(extraction_script = es).count() > 1:
            # this is a failure mode induced by the system's allowing
            # duplicate QA Groups to be created for a single script
            return QAGroup.objects.filter(extraction_script = es).first()

        
        # Create a new QA Group for the ExtractionScript es
        qa_group = QAGroup.objects.create(extraction_script=es)
        # Collect all the ExtractedText object keys that are related
        # to the Script being QA'd and have not yet been checked
        doc_text_ids = list(ExtractedText.objects.filter(extraction_script=es,
                                                    qa_checked=False
                                                    ).values_list('pk',
                                                                flat=True))
        # If there are fewer than 100 related records, they make up the entire QA Group
        if len(doc_text_ids) < 100 and len(doc_text_ids) > 0:
            texts = ExtractedText.objects.filter(pk__in=doc_text_ids)
        # Otherwise sample 20 percent
        elif len(doc_text_ids) >= 100 :
            # Otherwise sample 20% of them
            random_20 = math.ceil(len(doc_text_ids)/5)
            shuffle(doc_text_ids)  # this is used to make random selection of texts
            texts = ExtractedText.objects.filter(pk__in=doc_text_ids[:random_20])
        else:
            # If there are no related ExtractedText records, something has gone wrong
            # Don't make a new QA Group with zero ExtractedTexts
            # print('The Script has no related ExtractedText records')
            texts = None

        # Set the qa_group attribute of each ExtractedText record to the new QA Group    
        if texts is not None:
            for text in texts:
                text.qa_group = qa_group
                text.save()

        # If the force_doc_id argument was populated, make sure it gets assigned 
        # to the new QA Group
        if force_doc_id is not None and ExtractedText.objects.filter(pk=force_doc_id).exists():
            text = ExtractedText.objects.get(pk=force_doc_id)
            text.qa_group = qa_group
            text.save()
        
        return qa_group

        
