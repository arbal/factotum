from django.contrib.auth.models import User
from django.db import models


class CommonInfo(models.Model):
    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,
        blank=True,
        help_text="Creation timestamp, inherited from CommonInfo.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        null=True,
        blank=True,
        help_text="Modification timestamp, inherited from CommonInfo.",
    )
    created_by = models.ForeignKey(
        User,
        related_name="+",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        help_text="User who created the record, inherited from CommonInfo.",
    )
    updated_by = models.ForeignKey(
        User,
        related_name="+",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        help_text="User who modified the record, inherited from CommonInfo",
    )

    class Meta:
        abstract = True
