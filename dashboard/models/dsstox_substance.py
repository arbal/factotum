from django.db import models
from .common_info import CommonInfo
from .extracted_chemical import ExtractedChemical
from .ingredient import Ingredient
from django.urls import reverse


class DSSToxSubstance(CommonInfo):

    extracted_chemical = models.ForeignKey(ExtractedChemical, on_delete=models.CASCADE, null=False, blank=False)
    # TODO: confirm that deleting an ExtractedChemical should delete related DSSToxSubstance objects
    ingredients = models.ManyToManyField(through='dashboard.DSSToxSubstanceToIngredient',
                                         to='dashboard.DSSToxSubstance')
    true_cas = models.CharField(max_length=50, null=True, blank=True)
    true_chemname = models.CharField(max_length=500, null=True, blank=True)
    rid = models.CharField(max_length=50, null=True, blank=True)
    sid = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.true_chemname

    def get_datadocument_url(self):
        return self.extracted_chemical.extracted_text.data_document.get_absolute_url()

    def indexing(self):
        obj = DSSToxSubstanceIndex(
            meta={'id': self.id},
            chem_name=self.true_chemname,
            true_cas=self.true_cas,
            true_chem_name=self.true_chemname,
            facet_model_name='DSSTox Substance',
        )
        obj.save()
        return obj.to_dict(include_meta=True)

    def get_absolute_url(self):
        return reverse('dsstox_substance', kwargs={'pk': self.pk})
