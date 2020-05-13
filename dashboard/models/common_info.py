from django.contrib.auth.models import User
from django.db import models


class CommonInfo(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    created_by = models.ForeignKey(
        User, related_name="+", on_delete=models.CASCADE, blank=True, null=True
    )
    updated_by = models.ForeignKey(
        User, related_name="+", on_delete=models.CASCADE, blank=True, null=True
    )

    class Meta:
        abstract = True
