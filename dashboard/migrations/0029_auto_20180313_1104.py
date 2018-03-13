# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2018-03-13 11:04
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0028_auto_20180313_1055'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExtractedChemical',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cas', models.CharField(blank=True, max_length=50, null=True)),
                ('chem_name', models.CharField(blank=True, max_length=500, null=True)),
                ('raw_min_comp', models.CharField(blank=True, max_length=100, null=True)),
                ('raw_max_comp', models.CharField(blank=True, max_length=100, null=True)),
                ('units', models.CharField(blank=True, choices=[('percent composition', 'percent composition'), ('weight fraction', 'weight fraction')], max_length=20)),
                ('report_funcuse', models.CharField(blank=True, max_length=100, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='ExtractedText',
            fields=[
                ('data_document', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='dashboard.DataDocument')),
                ('record_type', models.CharField(blank=True, max_length=50, null=True)),
                ('prod_name', models.CharField(blank=True, max_length=500, null=True)),
                ('doc_date', models.CharField(blank=True, max_length=10, null=True)),
                ('rev_num', models.CharField(blank=True, max_length=50, null=True)),
                ('qa_checked', models.BooleanField(default=False)),
                ('extraction_script', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dashboard.Script')),
            ],
        ),
        migrations.AddField(
            model_name='extractedchemical',
            name='extracted_text',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dashboard.ExtractedText'),
        ),
    ]
