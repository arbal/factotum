# Generated by Django 2.2.1 on 2019-05-14 10:07

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('dashboard', '0110_listpresence_tag_tweaks'),
    ]

    operations = [
        migrations.AddField(
            model_name='puctag',
            name='definition',
            field=models.TextField(blank=True, max_length=255, null=True),
        ),
    ]
