from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("dashboard", "0120_auto_20190712_1054")]

    operations = [
        migrations.RunSQL(
            """
            UPDATE dashboard_rawchem
            SET dsstox_id = NULL
            WHERE dsstox_id = 1090
            """
        ),
        migrations.RunSQL(
            """
            DELETE FROM dashboard_dsstoxlookup
            WHERE id = 1090
            """
        ),
    ]
