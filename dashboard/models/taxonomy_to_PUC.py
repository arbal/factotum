from django.db import models
from django.utils.translation import ugettext_lazy as _

from .common_info import CommonInfo


class TaxonomyToPUC(CommonInfo):
    """
    Each PUC can be related to multiple taxonomies.
    """

    PUC = models.ForeignKey("PUC", on_delete=models.CASCADE)
    taxonomy = models.ForeignKey("Taxonomy", on_delete=models.CASCADE)

    class Meta:
        unique_together = ["taxonomy", "PUC"]
        verbose_name = _("Taxonomy/PUC Association")
        verbose_name_plural = _("Taxonomy/PUC Associations")

    def __str__(self):
        return str(f"{self.taxonomy} -> {self.PUC}")
