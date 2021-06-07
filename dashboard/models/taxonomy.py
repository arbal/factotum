from django.db import models
from .common_info import CommonInfo


class Taxonomy(CommonInfo):
    """
    Taxonomies provide additional non-exclusive metadata for PUCs. Linking
    PUCs to taxonomies allows Factotum users to harmonize the PUC hierarchy
    with external modeling systems like SHEDS-MM.
    """

    title = models.CharField(max_length=250, blank=False, null=False)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        "Taxonomy", on_delete=models.CASCADE, null=True, blank=True
    )
    source = models.ForeignKey("TaxonomySource", on_delete=models.CASCADE)
    category_code = models.CharField(max_length=40, blank=True)
    last_edited_by = models.ForeignKey(
        "auth.User", on_delete=models.SET_DEFAULT, default=1
    )
    product_category = models.ManyToManyField("PUC", through="TaxonomyToPUC")

    class Meta:
        verbose_name_plural = "Taxonomies"

    def __str__(self):
        return str(self.title)
