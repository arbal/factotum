# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2018-02-27 09:33
from __future__ import unicode_literals

import dashboard.models.data_source
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0026_auto_20180208_0037'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='datadocument',
            name='data_source',
        ),
        migrations.AddField(
            model_name='datadocument',
            name='uploaded_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='datasource',
            name='estimated_records',
            field=models.PositiveIntegerField(default=47, validators=[dashboard.models.data_source.validate_nonzero]),
        ),
        migrations.AlterField(
            model_name='product',
            name='brand_name',
            field=models.CharField(blank=True, db_index=True, default='', max_length=200, null=True),
        ),
    ]
