# Generated by Django 2.2.6 on 2020-05-13 08:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("dashboard", "0162_created_by_updated_by")]

    operations = [
        migrations.AlterField(
            model_name="puc",
            name="kind",
            field=models.CharField(
                blank=True,
                choices=[
                    ("UN", "unknown"),
                    ("FO", "Formulation"),
                    ("AR", "Article"),
                    ("OC", "Occupation"),
                ],
                default="UN",
                help_text="kind",
                max_length=2,
            ),
        )
    ]
