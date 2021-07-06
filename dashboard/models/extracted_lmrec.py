from django.db import models

from .raw_chem import RawChem
from .common_info import CommonInfo

TYPE_CHOICES = (("R", "Reported"), ("C", "Computed"))
GENDER_CHOICES = (("M", "Male"), ("F", "Female"), ("A", "All"), ("O", "Other"))


class ExtractedLMRec(RawChem):
    """
    The ExtractedLMRec subclass of RawChem is used when the chemical is
    related to a Literature Monitoring document.  The Record contains relevant
    chemical information as well as is statistical information

    Its parent records use the `dashboard.models.extracted_lmdoc.ExtractedLMDoc` model.
    """

    study_location = models.CharField(max_length=200, blank=True, null=True)
    sampling_date = models.DateField(blank=True, null=True)
    population_description = models.CharField(max_length=200, blank=True, null=True)
    population_gender = models.CharField(
        max_length=30, choices=GENDER_CHOICES, blank=True, null=True
    )
    population_age = models.CharField(
        max_length=200,
        help_text="Age can be reported as age ranges, or descriptive groups (adults, children, etc.)",
        blank=True,
        null=True,
    )
    population_other = models.CharField(
        max_length=200,
        help_text="Used for occupational or other population stratifiers we want to retain at the chemical level.",
        blank=True,
        null=True,
    )
    sampling_method = models.CharField(max_length=200, blank=True, null=True)
    analytical_method = models.CharField(max_length=200, blank=True, null=True)
    medium = models.CharField(max_length=200, blank=True, null=True)
    harmonized_medium = models.ForeignKey(
        "HarmonizedMedium",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        default=None,
        related_name="record",
    )
    num_measure = models.IntegerField(null=True, blank=True)
    num_nondetect = models.IntegerField(null=True, blank=True)
    detect_freq = models.FloatField(null=True, blank=True)
    detect_freq_type = models.CharField(
        max_length=1, choices=TYPE_CHOICES, blank=True, null=True
    )
    LOD = models.FloatField("LOD", null=True, blank=True)
    LOQ = models.FloatField("LOQ", null=True, blank=True)

    @classmethod
    def auditlog_fields(cls):
        """Lists the fields to be included in the audit log triggers

        Returns:
            list -- a list of field names
        """
        return []

    def get_card_body_fields(self):
        return [
            {
                "name": self._meta.get_field(field).verbose_name,
                "value": getattr(self, field),
            }
            for field in [
                "study_location",
                "sampling_date",
                "population_description",
                "population_gender",
                "population_age",
                "population_other",
                "sampling_method",
                "analytical_method",
                "medium",
                "harmonized_medium",
                "num_measure",
                "num_nondetect",
                "detect_freq",
                "detect_freq_type",
                "LOD",
                "LOQ",
            ]
            if getattr(self, field)
        ]


class StatisticalValue(CommonInfo):
    """
    This contains statistical values for Literature Monitoring Records.

    Used in a many to one relationship to ExtractedLMRec.
    """

    record = models.ForeignKey(
        "ExtractedLMRec", on_delete=models.CASCADE, related_name="statistics"
    )

    name = models.CharField(max_length=30)
    value = models.FloatField()
    value_type = models.CharField(max_length=1, choices=TYPE_CHOICES)
    # It would be best to leave this non-standardized.
    # There are many ways to represent the units, so it would be difficult to make a standard list.
    stat_unit = models.CharField(max_length=30)

    def clean(self):
        # Strip whitespace from stat_unit
        self.stat_unit = self.stat_unit.strip()

    def __str__(self):
        return f"{self.name} {self.value} {self.stat_unit}"


class HarmonizedMedium(CommonInfo):
    """
    Standardized values for the Literature Monitoring record

    ExtractedLMRec
    """

    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name
