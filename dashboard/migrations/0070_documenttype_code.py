# Generated by Django 2.1.2 on 2018-10-31 15:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0069_auto_20181022_1325'),
    ]

    operations = [
        migrations.AddField(
            model_name='documenttype',
            name='code',
            field=models.CharField(blank=True, default='??', max_length=2),
        ),
    ]
