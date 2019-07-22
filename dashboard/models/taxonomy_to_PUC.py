from django.db import models
from .common_info import CommonInfo


class TaxonomyToPUC(CommonInfo):
    PUC = models.ForeignKey("PUC", on_delete=models.CASCADE)
    taxonomy = models.ForeignKey("Taxonomy", on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "Taxonomies to PUC's"
