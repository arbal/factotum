# Generated by Django 2.2.20 on 2021-09-09 11:47

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("dashboard", "0210_remove_extractedcomposition_script"),
    ]

    operations = [
        migrations.AddField(
            model_name="extractedtext",
            name="cleaning_qa_approved_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="cleaned_documents",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Cleaning QA approved by",
            ),
        ),
        migrations.AddField(
            model_name="extractedtext",
            name="cleaning_qa_approved_date",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="Cleaning QA approval date"
            ),
        ),
        migrations.AddField(
            model_name="extractedtext",
            name="cleaning_qa_checked",
            field=models.BooleanField(
                default=False, verbose_name="Cleaning QA approved"
            ),
        ),
        migrations.AddField(
            model_name="extractedtext",
            name="cleaning_qa_edited",
            field=models.BooleanField(default=False, verbose_name="Cleaning QA edited"),
        ),
        migrations.AddField(
            model_name="extractedtext",
            name="cleaning_qa_group",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="cleaned_documents",
                to="dashboard.QAGroup",
                verbose_name="Cleaning QA group",
            ),
        ),
    ]
