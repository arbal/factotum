from django.db import models
from django.utils.translation import ugettext_lazy as _
from taggit.models import TaggedItemBase

from .PUC import PUCTag
from .common_info import CommonInfo
from .product import Product


class ProductToTag(TaggedItemBase, CommonInfo):
    content_object = models.ForeignKey(Product, on_delete=models.CASCADE)
    tag = models.ForeignKey(
        PUCTag, on_delete=models.CASCADE, related_name="%(app_label)s_%(class)s_items"
    )

    def __str__(self):
        return str(self.id)

    class Meta:
        unique_together = ["content_object", "tag"]
        verbose_name = _("Product/PUC Association")
        verbose_name_plural = _("Product/PUC Associations")
