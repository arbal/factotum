from django.db import models

class RawChem(models.Model):
    raw_cas = models.CharField("Raw CAS", max_length=100, null=True, blank=True)
    raw_chem_name = models.CharField("Raw chemical name", max_length=500,
                                                        null=True, blank=True)
    temp_id = models.IntegerField(default=0, null=True, blank=True)
    temp_obj_name = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.raw_chem_name

