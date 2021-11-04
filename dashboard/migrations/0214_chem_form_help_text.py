# Generated by Django 2.2.20 on 2021-11-03 22:25

import dashboard.models.extracted_composition
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0213_cleaned_comp_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='extractedcomposition',
            name='ingredient_rank',
            field=models.PositiveIntegerField(blank=True, help_text='The numerical order the chemical ingredient appears in an ingredient list.', null=True, validators=[dashboard.models.extracted_composition.validate_ingredient_rank], verbose_name='Ingredient rank'),
        ),
        migrations.AlterField(
            model_name='extractedcomposition',
            name='raw_central_comp',
            field=models.CharField(blank=True, help_text='The concentration if a single number is given. If a range is listed or no concentration is specified, this field should be blank.', max_length=100, verbose_name='Central'),
        ),
        migrations.AlterField(
            model_name='extractedcomposition',
            name='raw_max_comp',
            field=models.CharField(blank=True, help_text='The upper limit of concentration specified by a range. If a single number is given or no concentration is specified, this field should be blank.', max_length=100, verbose_name='Maximum'),
        ),
        migrations.AlterField(
            model_name='extractedcomposition',
            name='raw_min_comp',
            field=models.CharField(blank=True, help_text='The lower limit of concentration specified by a range. If a single number is given or no concentration is specified, this field should be blank.', max_length=100, verbose_name='Minimum'),
        ),
        migrations.AlterField(
            model_name='extractedcomposition',
            name='unit_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='dashboard.UnitType', verbose_name='The unit type for the concentration, as reported in source document.'),
        ),
        migrations.AlterField(
            model_name='extractedcomposition',
            name='weight_fraction_type',
            field=models.ForeignKey(default='1', null=True, on_delete=django.db.models.deletion.PROTECT, to='dashboard.WeightFractionType', verbose_name='Reported (Default) refers to weight fractions calculated using composition data present on the source document, while Predicted values are generated via model.'),
        ),
        migrations.AlterField(
            model_name='functionaluse',
            name='report_funcuse',
            field=models.CharField(blank=True, help_text='The function an ingredient serves within a product, as reported in source document.', max_length=255, unique=True, verbose_name='Reported functional use'),
        ),
        migrations.AlterField(
            model_name='rawchem',
            name='component',
            field=models.CharField(blank=True, help_text='The product component for products with multiple parts or items in a set.', max_length=200, verbose_name='Component'),
        ),
    ]
