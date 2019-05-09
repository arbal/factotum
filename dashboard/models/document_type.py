from django.db import models
from .common_info import CommonInfo
from .group_type import GroupType

class DocumentTypeManager(models.Manager):
    def compatible(self, obj):
        ''' Returns a QuerySet of compatible DocumentTypes.
        Arguments:
            ``obj``
                a model related to GroupType
        '''
        if type(obj) is int:
            return (super()
                    .get_queryset()
                    .filter(group_types__id=obj))
        elif type(obj) is GroupType:
            return self.compatible(obj.pk)
        elif hasattr(obj, 'group_type'):
            return self.compatible(obj.group_type)
        elif hasattr(obj, 'data_group'):
            return self.compatible(obj.data_group)
        else:
            raise ValueError("Input does not seem to relate to GroupType.")


class DocumentType(CommonInfo):
    title = models.CharField(max_length=50, unique=True)
    description = models.TextField(null=True, blank=True)
    code = models.CharField(blank=True, max_length=2, default='??', unique=True)
    group_types = models.ManyToManyField(through='dashboard.DocumentTypeGroupTypeCompatibilty',
                                         to='dashboard.GroupType',
                                         related_name='groups')
    objects = DocumentTypeManager()

    def __str__(self):
        return self.title

    class Meta:
        ordering = ('title',)
