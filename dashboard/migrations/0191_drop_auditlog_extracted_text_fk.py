from django.db import migrations, connection


def drop_audit_log_extracted_text_fk(apps, schema_editor):
    with connection.cursor() as c:
        try:
            c.execute(
                """
                alter table dashboard_auditlog
                drop foreign key dashboard_auditlog_extracted_text_id_bf4860ab_fk_dashboard
                """
            )
        except Exception as e:
            print(e)


def empty_reverse_function(apps, schema_editor):
    # The reverse function is not required
    pass


class Migration(migrations.Migration):

    dependencies = [("dashboard", "0190_rawchem_provisional")]

    operations = [
        migrations.RunPython(
            code=drop_audit_log_extracted_text_fk,
            reverse_code=empty_reverse_function,
            atomic=True,
        )
    ]
