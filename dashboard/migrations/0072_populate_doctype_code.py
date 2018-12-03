# Generated by Django 2.1.2 on 2018-10-31 15:32

from django.db import migrations

def update_document_type_field(apps, schema_editor):

    dtype = apps.get_model('dashboard', 'DocumentType')

    update_dict = { 'Unidentified'               :'UN',
                    'MSDS'                       :'MS',
                    'SDS'                        :'SD',
                    'ingredient list'            :'IL',
                    'ingredient disclosure'      :'ID',
                    'chemical use disclosure'    :'CD',
                    'Memo'                       :'MO',
                    'journal article'            :'JA',
                    'poster'                     :'PO',
                    'professional society report':'SR',
                    'other survey/study'         :'OT',
                    }

    for d in dtype.objects.all():
        if d.title in update_dict.keys():
            d.code = update_dict[d.title]
            d.save()

class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0071_documenttype_code'),
    ]

    operations = [
        migrations.RunPython(update_document_type_field,
                            reverse_code=migrations.RunPython.noop),
    ]