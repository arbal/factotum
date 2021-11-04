from django.db import models
from model_utils import FieldTracker
from model_utils.managers import InheritanceManager

from .common_info import CommonInfo


class RawChem(CommonInfo):
    """
    The RawChem model is the base class for most of the object types that 
    occupy the position beneath ExtractedText in the object hierarchy. When
    a single document has multiple chemicals associated with it, whether as
    List Presence items from a CPCat document or as Composition items from 
    an ingredient list, the child objects inherit from the RawChem base class.
    A curated record is one with a foreign key in the DSSToxLookup field.
    """

    CHEM_DETECTED_CHOICES = (("1", "Yes"), ("0", "No"))

    extracted_text = models.ForeignKey(
        "ExtractedText",
        related_name="rawchem",
        on_delete=models.CASCADE,
        null=False,
        blank=False,
    )
    raw_cas = models.CharField(
        "Raw CAS",
        max_length=100,
        blank=True,
        help_text="Chemical abstract service registry number (CASRN) as reported in original study",
    )
    raw_chem_name = models.CharField(
        "Raw chemical name",
        max_length=1300,
        blank=True,
        help_text="Chemical name as reported in original study",
    )

    rid = models.CharField(max_length=50, blank=True, help_text="RID")
    dsstox = models.ForeignKey(
        "DSSToxLookup",
        related_name="curated_chemical",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    component = models.CharField(
        "Component", max_length=200, blank=True, help_text="The product component for products with multiple parts or items in a set."
    )
    # Ideally the chem_detected_flag would be a nullable boolean field. However,
    # bulk_update() seems to have a bug related to nullable booleans
    chem_detected_flag = models.CharField(
        "Chemical Detected",
        max_length=1,
        choices=CHEM_DETECTED_CHOICES,
        null=True,
        blank=True,
        help_text="Flag indicating whether a chemical was ever detected in the studied medium",
    )
    provisional = models.BooleanField(
        default=False,
        help_text="""When a RawChem record has a raw_chem_name and raw_cas combination that 
        has already been curated to a certain DSSToxLookup record (and to only one), 
        Factotum will automatically populate the DSSToxLookup foreign key. The provisional 
        field indicates that this assignment was automatically performed without a curator 
        involved.""",
    )

    class Meta:
        indexes = [
            models.Index(fields=["extracted_text", "dsstox", "component"]),
            # Manually added indexes in dashboard 0190.  Django does not support MySQL prefix index
            # https://dev.mysql.com/doc/refman/8.0/en/column-indexes.html#column-indexes-prefix
            #
            # models.Index(fields=["raw_chem_name"], name="dashboard_rawchem_20char_rawchemname_index"),
            # models.Index(fields=["raw_cas"], name="dashboard_rawchem_20char_rawcas_index"),
        ]

    objects = InheritanceManager()

    tracker = FieldTracker()

    class JSONAPIMeta:
        resource_name = "chemicalInstance"

    def __str__(self):
        return str(self.raw_chem_name) if self.raw_chem_name else ""

    @property
    def sid(self):
        """If there is no DSSToxLookup record via the 
        curated_chemical relationship, it evaluates to boolean False """
        try:
            return self.curated_chemical.sid
        except AttributeError:
            return False

    @property
    def data_group_id(self):
        return str(self.extracted_text.data_document.data_group_id)

    def clean(self):
        def whitespace(fld):
            if fld:
                return fld.startswith(" ") or fld.endswith(" ")
            else:
                return False

        if whitespace(self.raw_cas):
            self.raw_cas = self.raw_cas.strip()
        if whitespace(self.raw_chem_name):
            self.raw_chem_name = self.raw_chem_name.strip()

    @property
    def true_cas(self):
        return self.dsstox.true_cas if self.dsstox else None

    @property
    def true_chemname(self):
        return self.dsstox.true_chemname if self.dsstox else None

    @property
    def rendered_chemname(self):
        return self.dsstox.true_chemname if self.dsstox else self.raw_chem_name

    @property
    def rendered_cas(self):
        return self.dsstox.true_cas if self.dsstox else self.raw_cas

    @classmethod
    def auditlog_fields(cls):
        """Lists the fields to be included in the audit log triggers

        Returns:
            list -- a list of field names
        """
        return [
            "raw_cas",
            "raw_chem_name",
            "rid",
            "component",
            "chem_detected_flag",
            "dsstox_id",
        ]

    @classmethod
    def detail_fields(cls):
        """Lists the fields to be displayed on a detail form

        Returns:
            list -- a list of field names
        """
        return ["extracted_text", "raw_chem_name", "raw_cas", "chem_detected_flag"]
