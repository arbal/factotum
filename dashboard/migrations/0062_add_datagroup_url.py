from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("dashboard", "0061_auto_20180824_1044")]

    operations = [
        migrations.AddField(
            model_name="datagroup",
            name="url",
            field=models.CharField(blank=True, max_length=150),
        )
    ]
