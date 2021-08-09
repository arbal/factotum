from django.db import models
from dashboard.models import CommonInfo

TYPE_CHOICES = (("R", "Reported"), ("C", "Computed"))
NAME_CHOICES = (
    ("MEAN", "Mean"),
    ("MEDIAN", "Median"),
    ("MAX", "Max"),
    ("P75", "75th Percentile"),
    ("P95", "95th Percentile"),
    ("P99", "99th Percentile"),
    ("SE", "Standard Error"),
    ("SD", "Standard Deviation"),
)


class StatisticalValue(CommonInfo):
    """
    This contains statistical values for RawChem child records (currently Literature Monitoring Records).

    Used in a many to one relationship to RawChem.
    """

    rawchem = models.ForeignKey(
        "RawChem", on_delete=models.CASCADE, default=None, related_name="statistics"
    )
    name = models.CharField(
        "Statistic Name", max_length=30, choices=NAME_CHOICES, null=False, blank=False
    )
    value = models.FloatField("Statistic Value", null=False, blank=False)
    value_type = models.CharField(
        "Reported or Computed",
        max_length=1,
        null=False,
        blank=False,
        choices=TYPE_CHOICES,
    )
    # It would be best to leave this non-standardized.
    # There are many ways to represent the units, so it would be difficult to make a standard list.
    stat_unit = models.CharField(
        "Statistic Unit", max_length=30, null=False, blank=False
    )

    def clean(self):
        self.name = self.name.strip()
        self.stat_unit = self.stat_unit.strip()
        for k, v in TYPE_CHOICES:
            if self.value_type and self.value_type.lower() == v.lower():
                self.value_type = k

    def __str__(self):
        return f"{self.name} {self.value} {self.stat_unit}"