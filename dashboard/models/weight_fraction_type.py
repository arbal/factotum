from django.db import models
from .common_info import CommonInfo


class WeightFractionType(CommonInfo):
    """
    A controlled vocabulary for the weight fraction measurements assigned to 
    composition records.
    """

    title = models.CharField(max_length=50)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ("id",)
