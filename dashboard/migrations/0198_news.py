# Generated by Django 2.2.20 on 2021-06-25 15:51

import ckeditor.fields
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("dashboard", "0197_harmonizedmedium_description"),
    ]

    operations = [
        migrations.CreateModel(
            name="News",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Creation timestamp, inherited from CommonInfo.",
                        null=True,
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        help_text="Modification timestamp, inherited from CommonInfo.",
                        null=True,
                    ),
                ),
                ("subject", models.CharField(max_length=200)),
                ("body", ckeditor.fields.RichTextField()),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        help_text="User who created the record, inherited from CommonInfo.",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        help_text="User who modified the record, inherited from CommonInfo",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"verbose_name_plural": "News"},
        )
    ]
