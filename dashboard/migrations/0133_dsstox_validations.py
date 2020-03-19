# Generated by Django 2.2.1 on 2019-10-23 10:47

import dashboard.models.dsstox_lookup
from django.db import migrations, models


def remove_bad_dsstox(apps, schema_editor):
    DSSToxLookup = apps.get_model("dashboard", "DSSToxLookup")
    RawChem = apps.get_model("dashboard", "RawChem")
    rc = RawChem.objects.filter(dsstox__in=[10189, 8388])
    rc.update(dsstox=None, rid=None)
    dss = DSSToxLookup.objects.filter(pk__in=[10189, 8388])
    dss.delete()


class Migration(migrations.Migration):
    dependencies = [("dashboard", "0132_auditlog_triggers")]

    operations = [
        migrations.RunPython(remove_bad_dsstox, reverse_code=migrations.RunPython.noop),
        migrations.AlterField(
            model_name="dsstoxlookup",
            name="sid",
            field=models.CharField(
                max_length=50,
                unique=True,
                validators=[
                    dashboard.models.dsstox_lookup.validate_prefix,
                    dashboard.models.dsstox_lookup.validate_blank_char,
                ],
                verbose_name="DTXSID",
            ),
        ),
    ]