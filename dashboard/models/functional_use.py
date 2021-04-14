from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Q

from .common_info import CommonInfo


class FunctionalUse(CommonInfo):
    """
    Each `FunctionalUse` record is related to a chemical record from the `RawChem`
    inheritance hierarchy. 

    A record of the `ExtractedFunctionalUse` subclass can be related to more than 
    one `FunctionalUse` record. 

    The attributes of this model used to be stored as attributes of the chemical models. 
    Migration `0145` split it out into its own schema object and migrated the old fields
    into the new table.

    """

    chem = models.ForeignKey(
        "RawChem",
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="functional_uses",
    )

    category = models.ForeignKey(
        "FunctionalUseCategory", on_delete=models.SET_NULL, null=True, blank=True
    )
    report_funcuse = models.CharField(
        "Reported functional use", max_length=255, null=False, blank=True
    )
    extraction_script = models.ForeignKey(
        "Script",
        on_delete=models.CASCADE,
        limit_choices_to={"script_type": "FU"},
        null=True,
        blank=True,
    )

    def validate_report_funcuse_category(self):
        """Reported functional use strings may only be linked to one FunctionalUseCategory.
        """

        if (
            FunctionalUse.objects.filter(report_funcuse=self.report_funcuse)
            .exclude(
                Q(pk=self.pk) | Q(category=self.category) | Q(category__isnull=True)
            )
            .exists()
        ):
            raise ValidationError(
                {
                    "report_funcuse": (
                        "This reported functional use is already "
                        "associated with a different Functional Use Category."
                    )
                }
            )

    def __str__(self):
        return self.report_funcuse

    def clean(self):
        if self.report_funcuse == "" or self.report_funcuse is None:
            raise ValidationError({"report_funcuse": "Please delete if no value."})

        if self.category:
            self.validate_report_funcuse_category()

    @classmethod
    def auditlog_fields(cls):
        return ["report_funcuse","category"]
