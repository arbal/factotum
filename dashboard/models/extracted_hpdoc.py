from django.db import models

from dashboard.models import ExtractedText


class ExtractedHPDoc(ExtractedText):
    """
    This is the subclass of ExtractedText that is created when a user uploads 
    extracted data for a habits and practices source document. There is no 
    composition data in this type of record. The child records use the 
    `dashboard.extracted_habits_and_practices.ExtractedHabitsAndPractices` model.
    """

    extraction_completed = models.BooleanField(
        default=False, help_text="The human health data has been manually extracted."
    )
