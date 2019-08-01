# Generated by Django 2.2.1 on 2019-07-12 10:54

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("dashboard", "0119_longer_definition")]

    operations = [
        migrations.AlterField(
            model_name="datadocument",
            name="raw_category",
            field=models.CharField(blank=True, max_length=1000, null=True),
        ),
        migrations.AlterField(
            model_name="extractedchemical",
            name="report_funcuse",
            field=models.CharField(
                blank=True, max_length=255, null=True, verbose_name="Functional use"
            ),
        ),
        migrations.AlterField(
            model_name="extractedchemical",
            name="unit_type",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="dashboard.UnitType",
            ),
        ),
        migrations.AlterField(
            model_name="grouptype",
            name="code",
            field=models.CharField(blank=True, max_length=2, null=True, unique=True),
        ),
    ]
