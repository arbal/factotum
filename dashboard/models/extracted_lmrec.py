from django.db import models

from django_db_views.db_view import DBView

from .raw_chem import RawChem
from .common_info import CommonInfo

DETECT_FREQ_TYPE_CHOICES = (("R", "Reported"), ("C", "Computed"))
GENDER_CHOICES = (("M", "Male"), ("F", "Female"), ("A", "All"), ("O", "Other"))


class UnionExtractedLMHHRec(DBView):
    """
    This is a database view that unions the ExtractedLMRec and ExtractedHHRec
    tables
    """

    rawchem = models.ForeignKey(RawChem, on_delete=models.DO_NOTHING)
    medium = models.CharField(max_length=200, blank=True, null=True)
    harmonized_medium = models.ForeignKey(
        "HarmonizedMedium",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        default=None,
        related_name="lm_or_hh_record",
    )
    num_measure = models.TextField("Numeric Measure", null=True, blank=True)

    def __str__(self):
        return str(self.rawchem.raw_chem_name) if self.rawchem.raw_chem_name else ""

    view_definition = """
         (SELECT 
            dashboard_extractedlmrec.rawchem_ptr_id as id,
            dashboard_extractedlmrec.rawchem_ptr_id as rawchem_id,
            dashboard_extractedlmrec.rawchem_ptr_id,
            dashboard_extractedlmrec.medium,
            dashboard_extractedlmrec.num_measure,
            dashboard_extractedlmrec.harmonized_medium_id
        FROM
            dashboard_extractedlmrec
                INNER JOIN
            dashboard_rawchem ON (dashboard_extractedlmrec.rawchem_ptr_id = dashboard_rawchem.id)
        ) 
        UNION 
        (SELECT 
            dashboard_extractedhhrec.rawchem_ptr_id as id,
            dashboard_extractedhhrec.rawchem_ptr_id as rawchem_id,
            dashboard_extractedhhrec.rawchem_ptr_id,
            dashboard_extractedhhrec.medium,
            dashboard_extractedhhrec.num_measure,
            NULL AS harmonized_medium_id
        FROM
            dashboard_extractedhhrec
                INNER JOIN
            dashboard_rawchem ON (dashboard_extractedhhrec.rawchem_ptr_id = dashboard_rawchem.id)
                INNER JOIN
            dashboard_dsstoxlookup ON (dashboard_rawchem.dsstox_id = dashboard_dsstoxlookup.id)
        )
      """

    class JSONAPIMeta:
        resource_name = "unionLMRecHHRec"

    class Meta:
        managed = False
        db_table = "union_lmrec_hhrec"


class ExtractedLMRec(RawChem):
    """
    The ExtractedLMRec subclass of RawChem is used when the chemical is
    related to a Literature Monitoring document.  The Record contains relevant
    chemical information as well as is statistical information

    Its parent records use the `dashboard.models.extracted_lmdoc.ExtractedLMDoc` model.
    """

    study_location = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Location where the study was performed",
    )
    sampling_date = models.DateField(
        blank=True,
        null=True,
        help_text="Date or date range when the study was performed",
    )
    population_description = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="General description of the population studied",
    )
    population_gender = models.CharField(
        max_length=30,
        choices=GENDER_CHOICES,
        blank=True,
        null=True,
        help_text="Gender or genders of the population studied",
    )
    population_age = models.CharField(
        max_length=200,
        help_text="Age groups or age ranges studied in the population",
        blank=True,
        null=True,
    )
    population_other = models.CharField(
        max_length=200,
        help_text="Other population information such as occupation",
        blank=True,
        null=True,
    )
    sampling_method = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Reported method by which the media samples were collected",
    )
    analytical_method = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Reported method by which the media samples were analyzed",
    )
    medium = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Environmental or biological medium studied (as reported)",
    )
    harmonized_medium = models.ForeignKey(
        "HarmonizedMedium",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        default=None,
        related_name="lm_record",
        help_text="Medium harmonized to standard categories used in Factotum",
    )
    num_measure = models.IntegerField(
        null=True, blank=True, help_text="Total number of measurements taken"
    )
    num_nondetect = models.IntegerField(
        null=True, blank=True, help_text="Reported number of non-detects"
    )
    detect_freq = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Detection frequency",
        help_text="Detection frequency in the medium",
    )
    detect_freq_type = models.CharField(
        max_length=1,
        choices=DETECT_FREQ_TYPE_CHOICES,
        blank=True,
        null=True,
        verbose_name="Detection frequency type",
        help_text="Indicates whether the detection frequency was reported in study or computed by data curators",
    )
    LOD = models.FloatField(
        "LOD", null=True, blank=True, help_text="Analytical limit of detection"
    )
    LOQ = models.FloatField(
        "LOQ", null=True, blank=True, help_text="Analytical limit of quantification"
    )

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


class HarmonizedMedium(CommonInfo):
    """
    Standardized values for the Literature Monitoring record

    ExtractedLMRec
    """

    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name
