# Generated by Django 2.2.18 on 2021-07-02 00:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("dashboard", "0196_lm_models")]

    operations = [
        migrations.AddField(
            model_name="harmonizedmedium",
            name="description",
            field=models.TextField(blank=True),
        )
    ]
