from django.db import models
from .common_info import CommonInfo
from django.urls import reverse


class DSSToxLookup(CommonInfo):

    sid = models.CharField('DTXSID', max_length=50, null=False, blank=False, unique=True)
    true_cas = models.CharField('True CAS', max_length=50, null=True, blank=True)
    true_chemname = models.CharField('True chemical name', max_length=500, null=True, blank=True)

    def __str__(self):
        return self.true_chemname

    def get_absolute_url(self):
        return reverse('dsstox_lookup', kwargs={'pk': self.pk})



