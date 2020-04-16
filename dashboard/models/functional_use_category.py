from django.db import models
from .common_info import CommonInfo


class FunctionalUseCategory(CommonInfo):
    title = models.CharField(max_length=50)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ("title",)
        verbose_name_plural = "functional use categories"
