from django.db import models
from .common_info import CommonInfo
from .product import Product
from .data_document import DataDocument
from django.urls import reverse


class ProductDocument(CommonInfo):
	product = models.ForeignKey(Product, on_delete=models.CASCADE,
                                                        null=True, blank=True)
	document = models.ForeignKey(DataDocument, on_delete=models.CASCADE)

	def __str__(self):
		return '%s --> %s' % (self.product.title, self.document.title)

	def get_absolute_url(self):
		return reverse('product_detail', kwargs={'pk': self.pk})
