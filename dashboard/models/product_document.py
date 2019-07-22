from django.db import models
from django.apps import apps
from django.urls import reverse

from .common_info import CommonInfo
from .product import Product
from .data_document import DataDocument


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
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, null=True, blank=True
    )
    document = models.ForeignKey(DataDocument, on_delete=models.CASCADE)

    objects = ProductDocumentManager()

    def __str__(self):
        return "%s --> %s" % (self.product.title, self.document.title)

    def get_absolute_url(self):
        return reverse("product_detail", kwargs={"pk": self.pk})
