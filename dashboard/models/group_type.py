from django.db import models
from .common_info import CommonInfo


class GroupType(CommonInfo):
    """
    A data group's type determines the types of documents that can be assigned to the group. 
    The two-character code is the primary key.
    """

    title = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    code = models.CharField(max_length=2, unique=True, null=True, blank=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ("title",)
