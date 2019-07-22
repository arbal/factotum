from django.db import models
from .common_info import CommonInfo


class TaxonomySource(CommonInfo):
    title = models.CharField(max_length=100, blank=False, null=False)
    description = models.TextField(null=True, blank=True)
    last_edited_by = models.ForeignKey(
        "auth.User", on_delete=models.SET_DEFAULT, default=1
    )

    class Meta:
        verbose_name_plural = "Taxonomy Sources"

    def __str__(self):
        return str(self.title)
