from django.db import migrations


def update_unknown_products(apps, schema_editor):
    """
    Sets product titles of "unknown" to the document title
    """
    Product = apps.get_model("dashboard", "Product")
    for p in Product.objects.filter(title__iexact="unknown"):
        d = p.documents.first()
        if d is not None:
            p.title = d.title
            p.save()


class Migration(migrations.Migration):
    dependencies = [("dashboard", "0150_functional_use_category")]
    operations = [
        migrations.RunPython(
            update_unknown_products, reverse_code=migrations.RunPython.noop
        )
    ]
