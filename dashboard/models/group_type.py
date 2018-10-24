from django.db import models
from .common_info import CommonInfo


class GroupType(CommonInfo):
    title = models.CharField(max_length=50)
    description = models.TextField(null=True, blank=True)
    code = models.TextField(null=True, blank=True, max_length=10)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ('title',)
