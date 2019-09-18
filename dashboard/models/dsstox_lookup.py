from django.db import models
from django.urls import reverse

from .common_info import CommonInfo
from .product_document import ProductDocument
from .PUC import PUC


class DSSToxLookup(CommonInfo):

    sid = models.CharField(
        "DTXSID", max_length=50, null=False, blank=False, unique=True
    )
    true_cas = models.CharField("True CAS", max_length=50, null=True, blank=True)
    true_chemname = models.CharField(
        "True chemical name", max_length=500, null=True, blank=True
    )

    def __str__(self):
        return self.true_chemname

    def get_absolute_url(self):
        return reverse("dsstox_lookup", kwargs={"sid": self.sid})

    def save(self, *args, **kwargs):
        self.sid = self.sid.replace(" ", "")  # ensure no spaces for url
        super(DSSToxLookup, self).save(*args, **kwargs)

    @property
    def puc_count(self):
        pdocs = ProductDocument.objects.from_chemical(self)
        return PUC.objects.filter(products__in=pdocs.values("product")).count()

    @property
    def cumulative_puc_count(self):
        pdocs = ProductDocument.objects.from_chemical(self)
        pucs = PUC.objects.filter(products__in=pdocs.values("product"))
        titles = []
        for puc in pucs:
            titles += list(f for f in (puc.gen_cat, puc.prod_fam, puc.prod_type) if f)
        return len(set(titles))
