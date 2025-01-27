# Generated by Django 2.2.18 on 2021-08-25 11:28

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("dashboard", "0206_lmrec_help_text")]

    operations = [
        migrations.AlterField(
            model_name="statisticalvalue",
            name="name",
            field=models.CharField(
                choices=[
                    ("MEAN", "Mean"),
                    ("MEDIAN", "Median"),
                    ("MAX", "Max"),
                    ("P75", "75th Percentile"),
                    ("P95", "95th Percentile"),
                    ("P99", "99th Percentile"),
                    ("SE", "Standard Error"),
                    ("SD", "Standard Deviation"),
                ],
                help_text="Name of the measurement statistic",
                max_length=30,
                verbose_name="Statistic Name",
            ),
        ),
        migrations.AlterField(
            model_name="statisticalvalue",
            name="stat_unit",
            field=models.CharField(
                help_text="Units for the measurement statistic",
                max_length=30,
                verbose_name="Statistic Unit",
            ),
        ),
        migrations.AlterField(
            model_name="statisticalvalue",
            name="value",
            field=models.FloatField(
                help_text=" Value of measurement statistic",
                verbose_name="Statistic Value",
            ),
        ),
        migrations.AlterField(
            model_name="statisticalvalue",
            name="value_type",
            field=models.CharField(
                choices=[("R", "Reported"), ("C", "Computed")],
                help_text="Indicates whether the statistical value was reported in study or calculated by data curators",
                max_length=1,
                verbose_name="Reported or Computed",
            ),
        ),
    ]
