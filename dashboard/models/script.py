from django.db import models
from django.urls import reverse
from django.core.validators import URLValidator, MaxValueValidator, MinValueValidator

from .common_info import CommonInfo
from .data_document import DataDocument
from .extracted_text import ExtractedText
from .qa_notes import QASummaryNote


class Script(CommonInfo, QASummaryNote):
    """
    A script refers to external code used to process data. Factotum users and other 
    researchers run scripts to extract data from PDF files, to assign PUCs to products,
    and to perform other data cleaning tasks.
    For some data types, the script provides the aggregation unit for QA work.
    An `EX` type can serve as the `extraction_script` for an `ExtractedText` record,
    a 'DC' type can serve as the `cleaning_script` for the same record or another.
    """

    TYPE_CHOICES = (
        ("DL", "download"),
        ("EX", "extraction"),
        ("PC", "product categorization"),
        ("DC", "data cleaning"),
        ("FU", "functional use cleaning"),
    )

    title = models.CharField(max_length=50)
    url = models.CharField(max_length=225, blank=True, validators=[URLValidator()])
    qa_begun = models.BooleanField(default=False)
    script_type = models.CharField(
        max_length=2, choices=TYPE_CHOICES, blank=False, default="EX"
    )
    confidence = models.PositiveSmallIntegerField(
        "Confidence",
        blank=True,
        validators=[MaxValueValidator(100), MinValueValidator(1)],
        default=1,
    )

    def __str__(self):
        return str(self.title)

    def get_qa_group_count(self):
        if self.script_type == "DC":
            n = DataDocument.objects.filter(
                extractedtext__cleaning_qa_group__isnull=False,
                extractedtext__cleaning_script=self.pk,
            ).count()
        else:
            n = DataDocument.objects.filter(
                extractedtext__qa_group__isnull=False,
                extractedtext__extraction_script=self.pk,
            ).count()
        return n

    def get_qa_complete_extractedtext_count(self):
        if self.script_type == "DC":
            n = DataDocument.objects.filter(
                extractedtext__cleaning_qa_checked=True,
                extractedtext__cleaning_script=self.pk,
            ).count()
        else:
            n = DataDocument.objects.filter(
                extractedtext__qa_checked=True, extractedtext__extraction_script=self.pk
            ).count()
        return n

    def get_pct_checked(self, numeric=False):
        qa_group_count = self.get_qa_group_count()
        pct = (
            0
            if qa_group_count == 0
            else (self.get_qa_complete_extractedtext_count() / qa_group_count * 100)
        )
        if numeric:
            return pct
        return f"{pct:.0f} %"

    def qa_button_text(self):
        if self.qa_completed():
            return "QA Complete"
        elif self.qa_begun:
            return "Continue QA"
        else:
            return "Begin QA"

    def qa_completed(self):
        """
        Return true when the percent checked is 100% of QA Group count
        """
        return self.get_pct_checked(numeric=True) == 100

    def get_or_create_qa_group(self):
        qa_group = QAGroup.objects.filter(script=self, qa_complete=False).first()
        if not qa_group:
            qa_group = self.create_qa_group()
            self.qa_begun = True
            self.save()
        return qa_group

    def create_qa_group(self):
        """
        Creates a QA Group for the specified Script object;
        Use all the related ExtractedText records or, if there are more than 100,
        select 20% of them. 
        """
        # Specify the share of a script's ExtractedText objects (in percentage) that must be
        # approved in order for the script's QA sat
        QA_COMPLETE_PERCENTAGE = 0.2

        qa_group = QAGroup.objects.create(script=self)

        # Set the appropriate qa_group attribute of each ExtractedText record
        # to the new QA Group
        if self.script_type == "DC":
            texts = ExtractedText.objects.filter(cleaning_script=self).exclude(
                cleaning_qa_checked=True
            )
        else:
            texts = ExtractedText.objects.filter(
                extraction_script=self, qa_checked=False
            )

        # If fewer than 100 related records, they make up the entire QA Group
        if len(texts) >= 100:
            import math

            # Otherwise sample X% of them
            random_sample = math.ceil(len(texts) * QA_COMPLETE_PERCENTAGE)
            pks = list(
                texts.values_list("pk", flat=True).order_by("?")[:random_sample]
            )  # ? used for random selection
            texts = ExtractedText.objects.filter(pk__in=pks)

        if texts:
            if self.script_type == "DC":
                texts.update(cleaning_qa_group=qa_group)
            else:
                texts.update(qa_group=qa_group)

        return qa_group

    def add_to_qa_group(self, force_doc_id):
        """this method will always create a QAGroup and add the document to it.
        """
        qa_group = self.get_or_create_qa_group()
        text = ExtractedText.objects.get(pk=force_doc_id)
        if self.script_type == "DC":
            text.cleaning_qa_group = qa_group
        else:
            text.qa_group = qa_group
        text.save()
        return qa_group


class QAGroup(CommonInfo):
    """
    A QAGroup is a collection of data documents or records that must be reviewed together 
    before the data document or group can be considered cleaned.
    """

    script = models.ForeignKey(
        Script,
        on_delete=models.CASCADE,
        related_name="qa_group",
        blank=False,
        null=False,
        limit_choices_to={"script_type": "EX", "script_type": "DC"},
    )
    qa_complete = models.BooleanField(default=False)

    def __str__(self):
        return str(self.script) + "_" + str(self.pk)
