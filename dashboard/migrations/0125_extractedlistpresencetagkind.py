from datetime import datetime

import django.db.models.deletion
import django.db.models.query
from django.db import migrations, models
from django.db.models import Case, IntegerField, Value, When


def insert_kinds_fwd(apps, schema_editor):
    ExtractedListPresenceTagKind = apps.get_model(
        "dashboard", "ExtractedListPresenceTagKind"
    )
    original_merge_time = datetime.fromtimestamp(1561146240)
    db_alias = schema_editor.connection.alias
    ExtractedListPresenceTagKind.objects.using(db_alias).bulk_create(
        [
            ExtractedListPresenceTagKind(
                pk=1,
                name="General use",
                created_at=original_merge_time,
                updated_at=datetime.now(),
            ),
            ExtractedListPresenceTagKind(
                pk=2,
                name="Pharmaceutical",
                created_at=original_merge_time,
                updated_at=datetime.now(),
            ),
            ExtractedListPresenceTagKind(
                pk=3,
                name="List presence",
                created_at=original_merge_time,
                updated_at=datetime.now(),
            ),
        ]
    )


def insert_kinds_rev(apps, schema_editor):
    ExtractedListPresenceTagKind = apps.get_model(
        "dashboard", "ExtractedListPresenceTagKind"
    )
    db_alias = schema_editor.connection.alias
    ExtractedListPresenceTagKind.objects.using(db_alias).filter(
        id__in=(1, 2, 3)
    ).delete()


def update_kind_fwd(apps, schema_editor):
    ExtractedListPresenceTag = apps.get_model("dashboard", "ExtractedListPresenceTag")
    db_alias = schema_editor.connection.alias
    ExtractedListPresenceTag.objects.using(db_alias).update(
        kind=Case(
            When(kind_bak="GU", then=Value(1)),
            When(kind_bak="PH", then=Value(2)),
            When(kind_bak="LP", then=Value(3)),
            output_field=IntegerField(),
        )
    )


def update_kind_rev(apps, schema_editor):
    ExtractedListPresenceTag = apps.get_model("dashboard", "ExtractedListPresenceTag")
    db_alias = schema_editor.connection.alias
    ExtractedListPresenceTag.objects.using(db_alias).update(kind=1)


class Migration(migrations.Migration):

    dependencies = [("dashboard", "0124_doc_url_length")]

    operations = [
        migrations.CreateModel(
            name="ExtractedListPresenceTagKind",
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
                ("name", models.CharField(max_length=50, unique=True)),
            ],
            options={
                "abstract": False,
                "verbose_name": "Extracted list presence keyword kind",
                "verbose_name_plural": "Extracted list presence keyword kinds",
            },
        ),
        migrations.RunPython(insert_kinds_fwd, insert_kinds_rev),
        migrations.RenameField(
            model_name="extractedlistpresencetag", old_name="kind", new_name="kind_bak"
        ),
        migrations.AddField(
            model_name="extractedlistpresencetag",
            name="kind",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.PROTECT,
                to="dashboard.ExtractedListPresenceTagKind",
            ),
            preserve_default=True,
        ),
        migrations.RunPython(update_kind_fwd, update_kind_rev),
        migrations.RemoveField(model_name="extractedlistpresencetag", name="kind_bak"),
    ]
