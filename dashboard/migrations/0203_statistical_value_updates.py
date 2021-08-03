# Generated by Django 2.2.22 on 2021-07-27 08:59

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [("dashboard", "0202_news_section_upload")]

    operations = [
        migrations.RemoveField(model_name="statisticalvalue", name="record"),
        migrations.AddField(
            model_name="statisticalvalue",
            name="rawchem",
            field=models.ForeignKey(
                default=None,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="statistics",
                to="dashboard.RawChem",
            ),
        ),
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
                max_length=30,
                verbose_name="Statistic Name",
            ),
        ),
        migrations.AlterField(
            model_name="statisticalvalue",
            name="stat_unit",
            field=models.CharField(max_length=30, verbose_name="Statistic Unit"),
        ),
        migrations.AlterField(
            model_name="statisticalvalue",
            name="value",
            field=models.FloatField(verbose_name="Statistic Value"),
        ),
        migrations.AlterField(
            model_name="statisticalvalue",
            name="value_type",
            field=models.CharField(
                choices=[("R", "Reported"), ("C", "Computed")],
                max_length=1,
                verbose_name="Reported or Computed",
            ),
        ),
    ]
