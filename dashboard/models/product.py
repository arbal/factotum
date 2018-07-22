from django.db import models
from .common_info import CommonInfo
from .data_source import DataSource
from .source_category import SourceCategory
#from .product_to_puc import ProductToPUC
#from .PUC import PUC
from django.urls import reverse


class Product(CommonInfo):
    data_source = models.ForeignKey(DataSource, related_name='source',
                                    on_delete=models.CASCADE)
    documents = models.ManyToManyField(through='dashboard.ProductDocument',
									   to='dashboard.DataDocument')
    ingredients = models.ManyToManyField(through='dashboard.ProductToIngredient',
										 to='dashboard.Ingredient')
    attributes = models.ManyToManyField(through='dashboard.ProductToAttribute',
										to='dashboard.ProductAttribute')
    source_category = models.ForeignKey(SourceCategory,
                                        on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=255)
    manufacturer = models.CharField(db_index=True, max_length=250,
                            null=True, blank=True, default = '')
    upc = models.CharField(db_index=True, max_length=60, null=False,
                            blank=False, unique=True)
    url = models.CharField(max_length=500, null=True, blank=True)
    brand_name = models.CharField(db_index=True, max_length=200, null=True,
                            blank=True, default = '')
    size = models.CharField(max_length=100, null=True, blank=True)
    model_number = models.CharField(max_length=200, null=True, blank=True)
    color = models.CharField(max_length=100, null=True, blank=True)
    item_id = models.IntegerField(null=True, blank=True)
    parent_item_id = models.IntegerField(null=True, blank=True)
    short_description = models.TextField(null=True, blank=True)
    long_description = models.TextField(null=True, blank=True)
    thumb_image = models.CharField(max_length=500, null=True, blank=True)
    medium_image = models.CharField(max_length=500, null=True, blank=True)
    large_image = models.CharField(max_length=500, null=True, blank=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('product_detail', kwargs={'pk': self.pk})

    def get_uber_product_to_puc(self):
        pucs = self.producttopuc_set
        if pucs.filter(classification_method='MA').count() == 1:
            return pucs.filter(classification_method='MA').first()
        elif pucs.filter(classification_method='AU').count() == 1:
            return pucs.filter(classification_method='AU').first()
        else:
            return None

    def get_uber_puc(self):
        thispuc = self.get_uber_product_to_puc()
        if thispuc is not None:
            return thispuc.PUC
        else:
            return None

    class Meta:
          ordering = ['-created_at']
