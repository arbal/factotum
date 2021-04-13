# Generated by Django 2.2.19 on 2021-03-31 12:15
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def transfer_to_functionalusetorawchem(apps, schema_editor):
    """Migrates all chemical data from FunctionalUse to FunctionalUseToRawChem; Deletes extra Functional Uses
    """
    FunctionalUse = apps.get_model("dashboard", "FunctionalUse")
    FunctionalUseToRawChem = apps.get_model("dashboard", "FunctionalUseToRawChem")

    chemical_connections = []

    for report_funcuse in FunctionalUse.objects.values_list(
        "report_funcuse", flat=True
    ).distinct():
        # Get all similar report_funcuses
        same_reports = FunctionalUse.objects.filter(report_funcuse=report_funcuse).all()
        main_report = same_reports[0]

        try:
            assigned_category = (
                FunctionalUse.objects.filter(
                    report_funcuse=report_funcuse, category__isnull=False
                )
                .order_by("extraction_script")
                .select_related("category")
                .first()
            )

            # Update new "main" functional use to contain extraction data.
            if assigned_category:
                main_report.category = assigned_category.category
                main_report.extraction_script = assigned_category.extraction_script
                main_report.save()
        except FunctionalUse.DoesNotExist:
            pass  # Pass if there are no assigned categories.

        # Verifies uniqueness
        chem_set = set()
        # Tie all functional uses to the first functional use (we will be keeping this one)
        for use in same_reports:
            if use.chem_id not in chem_set:
                chemical_connections.append(
                    FunctionalUseToRawChem(
                        chemical=use.chem, functional_use=main_report
                    )
                )
                chem_set.add(use.chem_id)

        # Delete redundant functional uses
        same_reports.exclude(pk=main_report.pk).delete()

    FunctionalUseToRawChem.objects.bulk_create(chemical_connections, batch_size=5000)


def transfer_from_functionalusetorawchem(apps, schema_editor):
    """Reverse migrating all chemical data from FunctionalUseToRawChem to FunctionalUse; Adds Functional Uses
    """
    FunctionalUse = apps.get_model("dashboard", "FunctionalUse")
    FunctionalUseToRawChem = apps.get_model("dashboard", "FunctionalUseToRawChem")

    functional_use_updates = []
    functional_use_creates = []

    # Iterate through all functional_use's connections
    for functional_use in FunctionalUseToRawChem.objects.values_list(
        "functional_use", flat=True
    ).distinct():
        # Load RawChem records pointing at the same FunctionalUse
        same_functional_uses = FunctionalUseToRawChem.objects.filter(
            functional_use_id=functional_use
        ).all()

        # Reattach first row for update
        first_functional_use = same_functional_uses[0].functional_use
        first_functional_use.chem = same_functional_uses[0].chemical
        functional_use_updates.append(first_functional_use)

        # Add new functional uses for all previously deleted functional uses.
        for same_functional_use in same_functional_uses[1:]:
            functional_use_creates.append(
                FunctionalUse(
                    report_funcuse=first_functional_use.report_funcuse,
                    category=first_functional_use.category,
                    extraction_script=first_functional_use.extraction_script,
                    chem=same_functional_use.chemical,
                )
            )

    FunctionalUse.objects.bulk_create(functional_use_creates, batch_size=5000)
    FunctionalUse.objects.bulk_update(
        functional_use_updates, fields=["chem"], batch_size=5000
    )


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("dashboard", "0186_remove_views"),
    ]
    operations = [
        migrations.CreateModel(
            name="FunctionalUseToRawChem",
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
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
            ],
            options={"abstract": False},
        ),
        migrations.AddIndex(
            model_name="functionaluse",
            index=models.Index(
                fields=["report_funcuse"], name="dashboard_f_report__5f31be_idx"
            ),
        ),
        migrations.AddField(
            model_name="functionalusetorawchem",
            name="chemical",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="dashboard.RawChem"
            ),
        ),
        migrations.AddField(
            model_name="functionalusetorawchem",
            name="functional_use",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to="dashboard.FunctionalUse",
            ),
        ),
        migrations.AddField(
            model_name="functionalusetorawchem",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="functionalusetorawchem",
            name="updated_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="functionaluse",
            name="chemicals",
            field=models.ManyToManyField(
                related_name="functional_uses",
                through="dashboard.FunctionalUseToRawChem",
                to="dashboard.RawChem",
            ),
        ),
        migrations.RunPython(
            code=transfer_to_functionalusetorawchem,
            reverse_code=transfer_from_functionalusetorawchem,
            elidable=True,
            atomic=True,
        ),
        migrations.AlterUniqueTogether(
            name="functionalusetorawchem",
            unique_together={("chemical", "functional_use")},
        ),
        migrations.AlterField(
            model_name="functionaluse",
            name="report_funcuse",
            field=models.CharField(
                blank=True,
                max_length=255,
                unique=True,
                verbose_name="Reported functional use",
            ),
        ),
        migrations.RemoveField(model_name="functionaluse", name="chem"),
    ]