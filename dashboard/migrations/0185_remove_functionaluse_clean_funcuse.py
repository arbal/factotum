# Generated by Django 2.2.17 on 2021-03-14 13:29

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("dashboard", "0184_extractedfunctionaluse_qa_flag")]

    operations = [
        migrations.RemoveField(model_name="functionaluse", name="clean_funcuse")
    ]
