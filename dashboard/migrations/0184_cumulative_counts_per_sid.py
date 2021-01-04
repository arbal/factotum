# Generated by Django 2.2.17 on 2020-12-31 14:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("dashboard", "0183_cumulative_counts_per_sid")]

    operations = [
        migrations.CreateModel(
            name="CumulativeProductsPerPucAndSid",
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
                ("cumulative_product_count", models.IntegerField()),
                ("product_count", models.IntegerField()),
                ("puc_level", models.IntegerField()),
            ],
            options={
                "db_table": "cumulative_products_per_puc_and_sid",
                "managed": False,
            },
        ),
        migrations.CreateModel(
            name="ProductsPerPucAndSid",
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
                ("product_count", models.IntegerField()),
            ],
            options={"db_table": "products_per_puc_and_sid", "managed": False},
        ),
        migrations.AlterField(
            model_name="puc",
            name="gen_cat",
            field=models.CharField(
                db_index=True, help_text="general category", max_length=50
            ),
        ),
        migrations.AlterField(
            model_name="puc",
            name="prod_fam",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text="product family",
                max_length=50,
            ),
        ),
        migrations.AlterField(
            model_name="puc",
            name="prod_type",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text="product type",
                max_length=100,
            ),
        ),
    ]
