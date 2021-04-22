from django.conf import settings
from django.db import migrations


def convert_functional_use_id_audit_entries(apps, schema_editor):
    def get_reported_harmonized(fu_id):
        reported = None
        harmonized = None
        try:
            fu = FunctionalUse.objects.get(id=fu_id)
            reported = fu.report_funcuse
            if fu.category_id is not None:
                harmonized = FunctionalUseCategory.objects.get(id=fu.category_id).title
        except FunctionalUse.DoesNotExist:
            pass
        return reported, harmonized

    AuditLog = apps.get_model("dashboard", "AuditLog")
    FunctionalUse = apps.get_model("dashboard", "FunctionalUse")
    FunctionalUseCategory = apps.get_model("dashboard", "FunctionalUseCategory")

    fu_id_entries = AuditLog.objects.filter(
        model_name="functionalusetorawchem", field_name="functional_use_id"
    )

    for entry in fu_id_entries:
        old_reported = None
        new_reported = None
        old_cat = None
        new_cat = None

        if entry.old_value is not None:
            old_reported, old_cat = get_reported_harmonized(entry.old_value)

        if entry.new_value is not None:
            new_reported, new_cat = get_reported_harmonized(entry.new_value)

        # add entry for report_funcuse
        if old_reported != new_reported:
            reported_entry = AuditLog.objects.create(
                object_key=entry.object_key,
                model_name=entry.model_name,
                field_name="report_funcuse",
                old_value=old_reported,
                new_value=new_reported,
                date_created=entry.date_created,
                action=entry.action,
                user_id=entry.user_id,
                extracted_text_id=entry.extracted_text_id,
                rawchem_id=entry.rawchem_id,
            )
            # work around the auto_now_add
            reported_entry.date_created = entry.date_created
            reported_entry.save()

        # add entry for harmonized category
        if old_cat != new_cat:
            harmonized_entry = AuditLog.objects.create(
                object_key=entry.object_key,
                model_name=entry.model_name,
                field_name="harmonized category",
                old_value=old_cat,
                new_value=new_cat,
                date_created=entry.date_created,
                action=entry.action,
                user_id=entry.user_id,
                extracted_text_id=entry.extracted_text_id,
                rawchem_id=entry.rawchem_id,
            )
            # work around the auto_now_add
            harmonized_entry.date_created = entry.date_created
            harmonized_entry.save()

        # delete original entry
        entry.delete()


def empty_reverse_function(apps, schema_editor):
    # The reverse function is not required
    pass


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("dashboard", "0187_add_functionalusetorawchem_model"),
    ]

    operations = [
        migrations.RunPython(
            code=convert_functional_use_id_audit_entries,
            reverse_code=empty_reverse_function,
            elidable=True,
            atomic=True,
        )
    ]
