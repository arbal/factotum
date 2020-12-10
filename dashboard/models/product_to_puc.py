from django.db import models

from .PUC import PUC
from .common_info import CommonInfo
from .product import Product
from django.utils.translation import ugettext_lazy as _


class ProductToPUC(CommonInfo):

    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    puc = models.ForeignKey(PUC, on_delete=models.CASCADE)
    puc_assigned_usr = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True, blank=True
    )
    puc_assigned_script = models.ForeignKey(
        "Script", on_delete=models.SET_NULL, null=True, blank=True
    )
    classification_method = models.ForeignKey(
        "ProductToPucClassificationMethod",
        max_length=3,
        on_delete=models.PROTECT,
        null=False,
        blank=False,
    )
    classification_confidence = models.DecimalField(
        max_digits=6, decimal_places=3, default=1, null=True, blank=True
    )

    def __str__(self):
        return f"{self.product} --> {self.puc}"

    class Meta:
        unique_together = ("product", "puc", "classification_method")


class ProductToPucClassificationMethodManager(models.Manager):
    def get_by_natural_key(self, code):
        return self.get(code=code)


class ProductToPucClassificationMethod(CommonInfo):
    code = models.CharField(
        max_length=3,
        primary_key=True,
        verbose_name="classification method code",
        db_column="id",
    )
    name = models.CharField(
        max_length=100, unique=True, verbose_name="classification method name"
    )
    rank = models.PositiveSmallIntegerField(
        unique=True, verbose_name="classification method rank"
    )

    def natural_key(self):
        return (self.code,)

    def get_by_natural_key(self, code):
        return self.get(code=code)

    objects = ProductToPucClassificationMethodManager()

    class Meta:
        ordering = ["rank"]
        verbose_name = _("PUC classification method")
        verbose_name_plural = _("PUC classification methods")

    def __str__(self):
        return f"{self.code} ({self.name})"
