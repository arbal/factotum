from django.db import models
from .common_info import CommonInfo


class UnitType(CommonInfo):
    """
    A controlled vocabulary for units of measure.
    """

    title = models.CharField("Unit Type", max_length=50)
    description = models.TextField("Unit Type", blank=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ("title",)
