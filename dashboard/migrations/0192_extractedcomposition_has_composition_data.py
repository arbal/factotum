# Generated by Django 2.2.19 on 2021-05-20 14:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("dashboard", "0191_drop_auditlog_extracted_text_fk")]

    operations = [
        migrations.AddField(
            model_name="extractedcomposition",
            name="has_composition_data",
            field=models.BooleanField(default=True),
        )
    ]
