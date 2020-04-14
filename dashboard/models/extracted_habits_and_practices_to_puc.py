from django.db import models

from .common_info import CommonInfo
from .extracted_habits_and_practices import ExtractedHabitsAndPractices


class ExtractedHabitsAndPracticesToPUC(CommonInfo):
    extracted_habits_and_practices = models.ForeignKey(
        ExtractedHabitsAndPractices, on_delete=models.CASCADE
    )
    PUC = models.ForeignKey("PUC", on_delete=models.CASCADE)

    def __str__(self):
        return str(self.id)

    class Meta:
        unique_together = ["extracted_habits_and_practices", "PUC"]
        verbose_name = "Extracted Habits and Practices/PUC Association"
        verbose_name_plural = "Extracted Habits and Practices/PUC Associations"
