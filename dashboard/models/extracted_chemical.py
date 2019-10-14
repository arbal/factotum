from six import text_type

from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import F

from .raw_chem import RawChem
from .unit_type import UnitType
from .common_info import CommonInfo
from .weight_fraction_type import WeightFractionType


def validate_ingredient_rank(value):
    if value < 1 or value > 999:
        raise ValidationError(
            (f"Quantity {value} is not allowed"), params={"value": value}
        )


class ExtractedChemical(CommonInfo, RawChem):

    raw_min_comp = models.CharField("Minimum", max_length=100, null=True, blank=True)
    raw_max_comp = models.CharField("Maximum", max_length=100, null=True, blank=True)
    unit_type = models.ForeignKey(
        UnitType,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="Unit type",
    )
    report_funcuse = models.CharField(
        "Reported functional use", max_length=255, null=True, blank=True
    )
    weight_fraction_type = models.ForeignKey(
        WeightFractionType,
        on_delete=models.PROTECT,
        null=True,
        default="1",
        verbose_name="Weight fraction type",
    )
    ingredient_rank = models.PositiveIntegerField(
        "Ingredient rank", null=True, blank=True, validators=[validate_ingredient_rank]
    )
    raw_central_comp = models.CharField(
        "Central", max_length=100, null=True, blank=True
    )
    component = models.CharField("Component", max_length=200, null=True, blank=True)

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
            "component",
        ]

    def get_datadocument_url(self):
        return self.extracted_text.data_document.get_absolute_url()

    @property
    def data_document(self):
        return self.extracted_text.data_document

    def get_extractedtext(self):
        return self.extracted_text

    @property
    def sid(self):
        if hasattr(self, "curated_chemical") and self.curated_chemical is not None:
            return self.curated_chemical.sid
        else:
            return None

    def __get_label(self, field):
        return text_type(self._meta.get_field(field).verbose_name)

    @property
    def raw_min_comp_label(self):
        return self.__get_label("raw_min_comp")

    @property
    def raw_central_comp_label(self):
        return self.__get_label("raw_central_comp")

    @property
    def raw_max_comp_label(self):
        return self.__get_label("raw_max_comp")

    @property
    def unit_type_label(self):
        return self.__get_label("unit_type")

    @property
    def report_funcuse_label(self):
        return self.__get_label("report_funcuse")

    @property
    def weight_fraction_type_label(self):
        return self.__get_label("weight_fraction_type")

    @property
    def ingredient_rank_label(self):
        return self.__get_label("ingredient_rank")

    @property
    def component_label(self):
        return self.__get_label("component")
