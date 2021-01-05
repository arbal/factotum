from django.db import models
from django.urls import reverse
from django.core.validators import URLValidator, MaxValueValidator, MinValueValidator

from .common_info import CommonInfo
from .data_document import DataDocument
from .extracted_text import ExtractedText
from .qa_notes import QASummaryNote


class Script(CommonInfo, QASummaryNote):

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

    def get_absolute_url(self):
        return reverse("extraction_script_edit", kwargs={"pk": self.pk})

    def get_qa_group_count(self):
        return DataDocument.objects.filter(
            extractedtext__qa_group__isnull=False, extractedtext__extraction_script=self.pk
        ).count()

    def get_qa_complete_extractedtext_count(self):
        return DataDocument.objects.filter(
            extractedtext__qa_checked=True, extractedtext__extraction_script=self.pk
        ).count()

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
        qa_group = QAGroup.objects.filter(
            extraction_script=self, qa_complete=False
        ).first()
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

        qa_group = QAGroup.objects.create(extraction_script=self)

        # Set the qa_group attribute of each ExtractedText record to the new QA Group
        texts = ExtractedText.objects.filter(extraction_script=self, qa_checked=False)

        # If fewer than 100 related records, they make up the entire QA Group
        if len(texts) >= 100:
            import math

            # Otherwise sample 20% of them
            random_sample = math.ceil(len(texts) * QA_COMPLETE_PERCENTAGE)
            pks = list(
                texts.values_list("pk", flat=True).order_by("?")[:random_sample]
            )  # ? used for random selection
            texts = ExtractedText.objects.filter(pk__in=pks)

        if texts:
            texts.update(qa_group=qa_group)

        return qa_group

    def add_to_qa_group(self, force_doc_id):
        """this method will always create a QAGroup and add the document to it.
        """
        qa_group = self.get_or_create_qa_group()
        text = ExtractedText.objects.get(pk=force_doc_id)
        text.qa_group = qa_group
        text.save()
        return qa_group


class QAGroup(CommonInfo):
    extraction_script = models.ForeignKey(
        Script,
        on_delete=models.CASCADE,
        related_name="qa_group",
        blank=False,
        null=False,
        limit_choices_to={"script_type": "EX"},
    )
    qa_complete = models.BooleanField(default=False)

    def __str__(self):
        return str(self.extraction_script) + "_" + str(self.pk)

    def get_approved_doc_count(self):
        return ExtractedText.objects.filter(qa_group=self, qa_checked=True).count()
