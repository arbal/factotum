from django.db import models
from .common_info import CommonInfo


class WeightFractionType(CommonInfo):
    title = models.CharField(max_length=50)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ("id",)
