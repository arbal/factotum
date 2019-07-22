from django.db import models
from .common_info import CommonInfo
from django.core.exceptions import ValidationError
from .unit_type import UnitType
from .weight_fraction_type import WeightFractionType
from .raw_chem import RawChem
from django.db.models import F


def validate_ingredient_rank(value):
    if value < 1 or value > 999:
        raise ValidationError(
            (f"Quantity {value} is not allowed"), params={"value": value}
        )


class ExtractedChemical(CommonInfo, RawChem):

    raw_min_comp = models.CharField("Minimum", max_length=100, null=True, blank=True)
    raw_max_comp = models.CharField("Maximum", max_length=100, null=True, blank=True)
    unit_type = models.ForeignKey(
        UnitType, on_delete=models.PROTECT, null=True, blank=True
    )
    report_funcuse = models.CharField(
        "Functional use", max_length=255, null=True, blank=True
    )
    weight_fraction_type = models.ForeignKey(
        WeightFractionType, on_delete=models.PROTECT, null=True, default="1"
    )
    ingredient_rank = models.PositiveIntegerField(
        "Ingredient rank", null=True, blank=True, validators=[validate_ingredient_rank]
    )
    raw_central_comp = models.CharField(
        "Central", max_length=100, null=True, blank=True
    )

    class Meta:
        ordering = (F("ingredient_rank").asc(nulls_last=True),)

    def __str__(self):
        return str(self.raw_chem_name) if self.raw_chem_name else ""

    def clean(self):
        # Don't allow the unit_type to be empty if there are raw_min_comp,
        # raw_central_comp, or raw_max_comp values.
        if (
            self.raw_min_comp or self.raw_central_comp or self.raw_max_comp
        ) and not self.unit_type:
            raise ValidationError(
                {
                    "unit_type": [
                        "There must be a unit type if a composition value is provided."
                    ]
                }
            )

    @classmethod
    def detail_fields(cls):
        return [
            "extracted_text",
            "raw_chem_name",
            "raw_cas",
            "raw_min_comp",
            "raw_central_comp",
            "raw_max_comp",
            "unit_type",
            "ingredient_rank",
            "report_funcuse",
            "weight_fraction_type",
            "rawchem_ptr",
        ]

    def get_datadocument_url(self):
        return self.extracted_text.data_document.get_absolute_url()

    @property
    def data_document(self):
        return self.extracted_text.data_document

    def indexing(self):
        obj = ExtractedChemicalIndex(
            meta={"id": self.id},
            chem_name=self.raw_chem_name,
            raw_cas=self.raw_cas,
            raw_chem_name=self.raw_chem_name,
            facet_model_name="Extracted Chemical",
        )
        obj.save()
        return obj.to_dict(include_meta=True)

    def get_extractedtext(self):
        return self.extracted_text

    @property
    def sid(self):
        if hasattr(self, "curated_chemical") and self.curated_chemical is not None:
            return self.curated_chemical.sid
        else:
            return None
