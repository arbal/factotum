from django.db import models
from .common_info import CommonInfo
from .group_type import GroupType


class DocumentType(CommonInfo):
    title = models.CharField(max_length=50)
    description = models.TextField(null=True, blank=True)
    code = models.CharField(blank=True, max_length=2, default='??')
    group_type = models.ForeignKey(GroupType, related_name='group',
                                                on_delete=models.PROTECT)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ('title',)
