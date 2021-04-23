from django.db import models

from dashboard.models import ExtractedText


class ExtractedHPDoc(ExtractedText):
    extraction_completed = models.BooleanField(default=False)
