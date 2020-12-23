# Generated by Django 2.2.14 on 2020-12-14 11:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("dashboard", "0177_duplicate_chemicals_view")]

    operations = [
        migrations.AddIndex(
            model_name="rawchem",
            index=models.Index(
                fields=["extracted_text", "dsstox", "component"],
                name="dashboard_r_extract_a5c3e2_idx",
            ),
        ),
        migrations.CreateModel(
            name="DuplicateChemicals",
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
                    "component",
                    models.CharField(
                        blank=True, max_length=200, verbose_name="Component"
                    ),
                ),
            ],
            options={"db_table": "duplicate_chemicals", "managed": False},
        ),
    ]