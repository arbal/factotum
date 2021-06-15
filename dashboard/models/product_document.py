from django.apps import apps
from django.db import models
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from .common_info import CommonInfo
from .data_document import DataDocument
from .product import Product


class ProductDocumentManager(models.Manager):
    def from_chemical(self, dsstox):
        """Retrieve a queryset of ProductDocuments where the 'document' is
        linked to an instance of DSSToxLookup, i.e. chemical.
        """
        if not type(dsstox) == apps.get_model("dashboard.DSSToxLookup"):
            raise TypeError("'dsstox' argument is not a DSSToxLookup instance.")
        return self.filter(
            document__extractedtext__rawchem__in=dsstox.curated_chemical.all()
        )


class ProductDocument(CommonInfo):
    """
    Because a single MSDS (or similar source document) can describe multiple 
    products offered in different packaging or variations, a data document can
    be related to multiple product records. There are several instances of
    multiple documents being linked to a single product, but those are likely 
    errors.
    """

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, null=True, blank=True
    )
    document = models.ForeignKey(DataDocument, on_delete=models.CASCADE)

    objects = ProductDocumentManager()

    def __str__(self):
        return "%s --> %s" % (self.product.title, self.document.title)

    class Meta:
        unique_together = ["product", "document"]
        verbose_name = _("Product/Document Association")
        verbose_name_plural = _("Product/Document Associations")

    def get_absolute_url(self):
        return reverse("product_detail", kwargs={"pk": self.pk})
