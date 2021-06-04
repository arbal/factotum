from django.db import models
from .common_info import CommonInfo
from dashboard.models import Product, DataDocument, RawChem, ProductDocument
from django.urls import reverse
from django.db.models import Q
from django.db.models import Count


class FunctionalUseCategory(CommonInfo):
    """
    Each reported functional use can be assigned to a "harmonized" category.
    This controlled vocabulary of harmonized categories is maintained by Factotum
    users.
    """

    title = models.CharField(max_length=50)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ("title",)
        verbose_name_plural = "functional use categories"

    def get_absolute_url(self):
        return reverse("functional_use_category_detail", args=(self.pk,))

    @property
    def product_count(self):
        return (
            Product.objects.filter(
                Q(datadocument__extractedtext__rawchem__functional_uses__category=self)
            )
            .distinct()
            .count()
        )

    @property
    def chemical_count(self):
        return (
            RawChem.objects.filter(Q(functional_uses__category=self))
            .values("dsstox")
            .distinct()
            .count()
        )

    @property
    def document_count(self):
        return (
            DataDocument.objects.filter(
                Q(extractedtext__rawchem__functional_uses__category=self)
            )
            .distinct()
            .count()
        )
