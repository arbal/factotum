from django.db import models
from .common_info import CommonInfo


class Taxonomy(CommonInfo):
    title = models.CharField(max_length=100, blank=False, null=False)
    description = models.TextField(null=True, blank=True)
    parent = models.ForeignKey('Taxonomy', on_delete=models.CASCADE,
                                                    null=True, blank=True)
    source = models.ForeignKey('TaxonomySource', on_delete=models.CASCADE)
    category_code = models.CharField(max_length=40, null=True, blank=True)
    last_edited_by = models.ForeignKey('auth.User',
                                                on_delete=models.SET_DEFAULT,
                                                default=1)
    product_category = models.ManyToManyField('PUC', through='TaxonomyToPUC')

    class Meta:
        verbose_name_plural = 'Taxonomies'

    def __str__(self):
        return str(self.title)
