# Generated by Django 2.2.12 on 2020-08-24 12:21

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("dashboard", "0167_puckind")]

    operations = [
        migrations.RemoveField(model_name="rawchem", name="temp_id"),
        migrations.RemoveField(model_name="rawchem", name="temp_obj_name"),
        migrations.AddField(
            model_name="rawchem",
            name="chem_detected_flag",
            field=models.CharField(
                blank=True,
                choices=[("1", "Yes"), ("0", "No")],
                max_length=1,
                null=True,
                verbose_name="Chemical Detected",
            ),
        ),
    ]
