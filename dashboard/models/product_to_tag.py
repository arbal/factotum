from django.db import models
from .common_info import CommonInfo
from .product import Product
from .PUC_tag import PUCTag
from taggit.models import TaggedItemBase

class ProductToTag(TaggedItemBase, CommonInfo):
	content_object = models.ForeignKey(Product, on_delete=models.CASCADE)
	tag = models.ForeignKey(PUCTag, on_delete=models.CASCADE,
							related_name="%(app_label)s_%(class)s_items")

	def __str__(self):
		return str(self.id)
