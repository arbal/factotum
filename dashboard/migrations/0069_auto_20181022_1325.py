# Generated by Django 2.1.2 on 2018-10-22 13:25

from django.db import migrations, models
import django.db.models.deletion
import taggit.managers


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0068_auto_20181019_1612'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='tags',
            field=taggit.managers.TaggableManager(help_text='A set of PUC Tags applicable to this Product', through='dashboard.ProductToTag', to='dashboard.PUCTag', verbose_name='Tags'),
        ),
        migrations.AlterField(
            model_name='producttotag',
            name='content_object',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dashboard.Product'),
        ),
        migrations.AlterField(
            model_name='producttotag',
            name='tag',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dashboard_producttotag_items', to='dashboard.PUCTag'),
        ),
        migrations.AlterField(
            model_name='puc',
            name='tags',
            field=taggit.managers.TaggableManager(help_text='A set of PUC Tags applicable to this PUC', through='dashboard.PUCToTag', to='dashboard.PUCTag', verbose_name='Tags'),
        ),
        migrations.AlterField(
            model_name='puctotag',
            name='content_object',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dashboard.PUC'),
        ),
        migrations.AlterField(
            model_name='puctotag',
            name='tag',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dashboard_puctotag_items', to='dashboard.PUCTag'),
        ),
    ]
