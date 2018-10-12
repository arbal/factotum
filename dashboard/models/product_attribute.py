from django.db import models
from .common_info import CommonInfo


class ProductAttribute(CommonInfo):
    title = models.CharField(max_length=75)
    type = models.CharField(max_length=75)
    products = models.ManyToManyField(through='dashboard.ProductToAttribute',
                                                to='dashboard.Product')

    def __str__(self):
        return self.title

    class Meta:
        ordering = ('title',)
