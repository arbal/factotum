# Generated by Django 2.2.20 on 2021-06-08 16:34

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [("feedback", "0003_comment_model_updates")]

    operations = [
        migrations.AlterField(
            model_name="comment",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True,
                help_text="Creation timestamp, inherited from CommonInfo.",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="comment",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                help_text="User who created the record, inherited from CommonInfo.",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="comment",
            name="updated_at",
            field=models.DateTimeField(
                auto_now=True,
                help_text="Modification timestamp, inherited from CommonInfo.",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="comment",
            name="updated_by",
            field=models.ForeignKey(
                blank=True,
                help_text="User who modified the record, inherited from CommonInfo",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]