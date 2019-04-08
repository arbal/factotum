from django.db import models
from .common_info import CommonInfo
from django.core.exceptions import ValidationError
from .extracted_text import ExtractedText
from .unit_type import UnitType
from .weight_fraction_type import WeightFractionType
from .raw_chem import RawChem


def validate_ingredient_rank(value):
    if value < 1 or value > 999:
        raise ValidationError(
            (f'Quantity {value} is not allowed'), params={'value': value},)


class ExtractedChemical(CommonInfo, RawChem):

    raw_cas_old = models.CharField(
        "Raw CAS", max_length=100, null=True, blank=True)
    raw_chem_name_old = models.CharField("Raw chemical name", max_length=500,
                                         null=True, blank=True)
    raw_min_comp = models.CharField("Raw minimum composition", max_length=100,
                                    null=True, blank=True)
    raw_max_comp = models.CharField("Raw maximum composition", max_length=100,
                                    null=True, blank=True)
    unit_type = models.ForeignKey(UnitType, on_delete=models.PROTECT)
    report_funcuse = models.CharField("Reported functional use", max_length=100,
                                      null=True, blank=True)
    weight_fraction_type = models.ForeignKey(WeightFractionType,
                                             on_delete=models.PROTECT, null=True, default='1')
    ingredient_rank = models.PositiveIntegerField("Ingredient rank", null=True, blank=True,
                                                  validators=[validate_ingredient_rank])
    raw_central_comp = models.CharField("Raw central composition", max_length=100, null=True, blank=True)

    def __str__(self):
        return str(self.raw_chem_name) if self.raw_chem_name else ''

    @classmethod
    def detail_fields(cls):
        return ['extracted_text', 'raw_chem_name', 'raw_cas', 'raw_min_comp', 'raw_central_comp',
                'raw_max_comp', 'unit_type', 'weight_fraction_type', 'report_funcuse',
                'ingredient_rank', 'rawchem_ptr']

    def get_datadocument_url(self):
        return self.extracted_text.data_document.get_absolute_url()

    @property
    def data_document(self):
        return self.extracted_text.data_document

    def indexing(self):
        obj = ExtractedChemicalIndex(
            meta={'id': self.id},
            chem_name=self.raw_chem_name,
            raw_cas=self.raw_cas,
            raw_chem_name=self.raw_chem_name,
            facet_model_name='Extracted Chemical',
        )
        obj.save()
        return obj.to_dict(include_meta=True)

    def get_extractedtext(self):
        return self.extracted_text

    @property
    def true_cas(self):
        if hasattr(self, 'curated_chemical') and self.curated_chemical is not None:
            return self.curated_chemical.true_cas
        else:
            return None

    @property
    def true_chemname(self):
        if hasattr(self, 'curated_chemical') and self.curated_chemical is not None:
            return self.curated_chemical.true_chemname
        else:
            return None

    @property
    def sid(self):
        if hasattr(self, 'curated_chemical') and self.curated_chemical is not None:
            return self.curated_chemical.sid
        else:
            return None
