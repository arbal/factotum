from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("dashboard", "0166_allow_blank_extr_scr"),
    ]

    operations = [
        migrations.CreateModel(
            name="PUCKind",
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
                (
                    "code",
                    models.CharField(blank=True, max_length=2, null=True, unique=True),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"verbose_name": "PUC kind", "verbose_name_plural": "PUC kinds"},
        ),
        migrations.RunSQL(
            sql="""INSERT INTO dashboard_puckind (name, code) values ('Unknown','UN');
                INSERT INTO dashboard_puckind (name, code) values ('Formulation','FO');
                INSERT INTO dashboard_puckind (name, code) values ('Article','AR');
                INSERT INTO dashboard_puckind (name, code) values ('Occupation','OC'); """,
            reverse_sql="DELETE FROM dashboard_puckind;",
        ),
        # Converting PUC.kind from char field to FK
        migrations.RunSQL(
            sql="""ALTER TABLE dashboard_puc CHANGE kind kind_temp VARCHAR(2);""",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.AddField(
            model_name="puc",
            name="kind",
            field=models.ForeignKey(
                default=1,
                help_text="kind",
                on_delete=django.db.models.deletion.CASCADE,
                to="dashboard.PUCKind",
            ),
        ),
        migrations.RunSQL(
            sql="""UPDATE dashboard_puc set kind_id = 
                CASE
                    WHEN kind_temp = 'UN' THEN 1
                    WHEN kind_temp = 'FO' THEN 2
                    WHEN kind_temp = 'AR' THEN 3
                    WHEN kind_temp = 'OC' THEN 4
                    ELSE NULL
                END;
                ALTER TABLE dashboard_puc DROP COLUMN kind_temp;
                """,
            reverse_sql="""
                ALTER TABLE dashboard_puc ADD kind VARCHAR(2);
                UPDATE dashboard_puc set kind = 
                    CASE
                        WHEN kind_id = 1 THEN 'UN'
                        WHEN kind_id = 2 THEN 'FO'
                        WHEN kind_id = 3 THEN 'AR'
                        WHEN kind_id = 4 THEN 'OC'
                        ELSE NULL
                    END;
                """,
        ),
    ]
