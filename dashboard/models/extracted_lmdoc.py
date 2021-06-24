from django.db import models

from dashboard.models import ExtractedText


class ExtractedLMDoc(ExtractedText):
    STUDY_TYPE_CHOICES = (
        ("Targeted", "Targeted"),
        ("Non-Targeted", "Non-Targeted or Suspect Screening"),
        ("Other", "Other"),
    )

    study_type = models.CharField(
        "Study Type", choices=STUDY_TYPE_CHOICES, max_length=12, blank=True
    )

    media = models.CharField("Media", max_length=100, blank=True)
    qa_flag = models.CharField(
        "QA flag",
        help_text="Indicates whether ICF completed QA",
        max_length=30,
        blank=True,
    )
    qa_who = models.CharField(
        "QA who",
        help_text="Name of contractor who completed QA",
        max_length=50,
        blank=True,
    )
    extraction_wa = models.TextField(
        help_text="Contain details of the contract and work assignment under which data was extracted",
        verbose_name="Extraction WA",
        blank=True,
    )

    def __str__(self):
        return str(self.data_document)
