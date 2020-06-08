from django.core.validators import RegexValidator
from django.db import models

from dashboard.models import ExtractedText


class ExtractedHPDoc(ExtractedText):
    pmid = models.CharField(
        "PMID",
        validators=[RegexValidator("^[0-9]*$", "PMID must be numerical")],
        max_length=20,
        blank=True,
    )
