from django.core.exceptions import ValidationError
from django.db import models
from six import text_type

from dashboard.models.common_info import CommonInfo


CHEM_DETECTED_CHOICES = (("YES", "Yes"), ("NO", "No"), ("UNDETERMINED", "Undetermined"))
DATA_TYPE_CHOICES = (("SUMMARY", "summary"), ("SINGLE", "single-sample"))


class MediaSampleSummary(CommonInfo):
    """
    These summary records are provided from outside the ChemExpoDB system
    """

    source_name = models.CharField(
        "Source Name",
        max_length=120,
        blank=True,
        help_text="Name of the original data source from where data was extracted and harmonized",
    )
    data_type = models.CharField(
        "Data Type",
        max_length=13,
        blank=True,
        help_text="Whether the original data source was reported as “summary” level data (mean, median, quartile, population, etc.) or “single-sample” level data ",
    )
    harmonized_medium = models.ForeignKey(
        "dashboard.HarmonizedMedium",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        default=None,
        related_name="mmdb_record",
        help_text="Unique tags used to harmonize across diverse media and species pairs.",
    )
    reported_medium = models.CharField(
        "Reported Medium",
        max_length=200,
        blank=True,
        help_text="Reported medium name in the raw data",
    )
    reported_species = models.CharField(
        "Reported Species",
        max_length=200,
        blank=True,
        help_text="Reported species name in the raw data",
    )
    dsstox = models.ForeignKey(
        "dashboard.DSSToxLookup",
        to_field="sid",
        related_name="mmdb_summary",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    number_of_observations = models.PositiveIntegerField(null=True, default=None)
    detected_sample_count = models.PositiveIntegerField(null=True, default=None)
    chem_detected_flag = models.CharField(
        "Chemical Detected",
        max_length=20,
        choices=CHEM_DETECTED_CHOICES,
        null=True,
        blank=True,
        help_text="Flag indicating whether a chemical was ever detected in the studied medium",
    )

    class JSONAPIMeta:
        resource_name = "mediasamplesummary"

    @classmethod
    def detail_fields(cls):
        """Lists the fields to be displayed on a detail form

        Returns:
            list -- a list of field names
        """
        return [
            "source_name",
            "data_type",
            "harmonized_medium",
            "reported_medium",
            "reported_species",
            "dsstox",
            "number_of_observations",
            "detected_sample_count",
            "chemical_detected",
        ]

    def __get_label(self, field):
        return text_type(self._meta.get_field(field).verbose_name)
