from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("dashboard", "0157_modify_hp_tag_ordering")]

    operations = [
        migrations.RunSQL(
            """
            DELETE FROM dashboard_taxonomytopuc WHERE id = 274;
            DELETE FROM dashboard_taxonomytopuc WHERE id = 292;
            """
        ),
        migrations.AlterModelOptions(
            name="extractedhabitsandpracticestopuc",
            options={
                "verbose_name": "Extracted Habits and Practices/PUC Association",
                "verbose_name_plural": "Extracted Habits and Practices/PUC Associations",
            },
        ),
        migrations.AlterModelOptions(
            name="productdocument",
            options={
                "verbose_name": "Product/Document Association",
                "verbose_name_plural": "Product/Document Associations",
            },
        ),
        migrations.AlterModelOptions(
            name="puctotag",
            options={"verbose_name": "PUC Tag", "verbose_name_plural": "PUC Tags"},
        ),
        migrations.AlterModelOptions(
            name="taxonomytopuc",
            options={
                "verbose_name": "Taxonomy/PUC Association",
                "verbose_name_plural": "Taxonomy/PUC Associations",
            },
        ),
        migrations.AlterModelOptions(
            name="producttotag",
            options={
                "verbose_name": "Product/PUC Association",
                "verbose_name_plural": "Product/PUC Associations",
            },
        ),
        migrations.AlterUniqueTogether(
            name="extractedhabitsandpracticestopuc",
            unique_together={("extracted_habits_and_practices", "PUC")},
        ),
        migrations.AlterUniqueTogether(
            name="extractedlistpresencetotag",
            unique_together={("content_object", "tag")},
        ),
        migrations.AlterUniqueTogether(
            name="productdocument", unique_together={("product", "document")}
        ),
        migrations.AlterUniqueTogether(
            name="puctotag", unique_together={("content_object", "tag")}
        ),
        migrations.AlterUniqueTogether(
            name="taxonomytopuc", unique_together={("taxonomy", "PUC")}
        ),
        migrations.AlterUniqueTogether(
            name="producttotag", unique_together={("content_object", "tag")}
        ),
    ]
