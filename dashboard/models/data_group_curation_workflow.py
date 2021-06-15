from django.db import models

from dashboard.models import CommonInfo


class CurationStep(CommonInfo):
    """
    The steps through which a data group travels during its curation workflow
    are named and ordered in this model.
    """

    name = models.CharField(
        max_length=100, unique=True, help_text="the curation step name"
    )
    step_number = models.PositiveSmallIntegerField(
        unique=True,
        help_text="the order number of the curation step to finish the workflow",
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ("step_number",)


class DataGroupCurationWorkflow(CommonInfo):
    """
    Each data group's curation workflow is described as a series of step/status combinations.
    """

    STEP_STATUS_CHOICES = (("I", "Incomplete"), ("C", "Complete"), ("N", "N/A"))
    data_group = models.ForeignKey(
        "DataGroup",
        on_delete=models.CASCADE,
        related_name="curation_steps",
        help_text="the DataGroup object associated with the curation step.",
    )
    curation_step = models.ForeignKey(
        CurationStep,
        on_delete=models.PROTECT,
        help_text="the CurationStep object in the workflow.",
    )
    step_status = models.CharField(
        max_length=1, choices=STEP_STATUS_CHOICES, default="I"
    )

    def __str__(self):
        return str(self.id)

    class Meta:
        unique_together = ["data_group", "curation_step"]
