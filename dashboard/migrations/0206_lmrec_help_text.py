# Generated by Django 2.2.22 on 2021-08-08 17:22

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [("dashboard", "0205_hpdoc_foreign_key")]

    operations = [
        migrations.AlterField(
            model_name="extractedlmrec",
            name="LOD",
            field=models.FloatField(
                blank=True,
                help_text="Analytical limit of detection",
                null=True,
                verbose_name="LOD",
            ),
        ),
        migrations.AlterField(
            model_name="extractedlmrec",
            name="LOQ",
            field=models.FloatField(
                blank=True,
                help_text="Analytical limit of quantification",
                null=True,
                verbose_name="LOQ",
            ),
        ),
        migrations.AlterField(
            model_name="extractedlmrec",
            name="analytical_method",
            field=models.CharField(
                blank=True,
                help_text="Reported method by which the media samples were analyzed",
                max_length=200,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="extractedlmrec",
            name="detect_freq",
            field=models.FloatField(
                blank=True,
                help_text="Detection frequency in the medium",
                null=True,
                verbose_name="Detection frequency",
            ),
        ),
        migrations.AlterField(
            model_name="extractedlmrec",
            name="detect_freq_type",
            field=models.CharField(
                blank=True,
                choices=[("R", "Reported"), ("C", "Computed")],
                help_text="Indicates whether the detection frequency was reported in study or computed by data curators",
                max_length=1,
                null=True,
                verbose_name="Detection frequency type",
            ),
        ),
        migrations.AlterField(
            model_name="extractedlmrec",
            name="harmonized_medium",
            field=models.ForeignKey(
                blank=True,
                default=None,
                help_text="Medium harmonized to standard categories used in Factotum",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="lm_record",
                to="dashboard.HarmonizedMedium",
            ),
        ),
        migrations.AlterField(
            model_name="extractedlmrec",
            name="medium",
            field=models.CharField(
                blank=True,
                help_text="Environmental or biological medium studied (as reported)",
                max_length=200,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="extractedlmrec",
            name="num_measure",
            field=models.IntegerField(
                blank=True, help_text="Total number of measurements taken", null=True
            ),
        ),
        migrations.AlterField(
            model_name="extractedlmrec",
            name="num_nondetect",
            field=models.IntegerField(
                blank=True, help_text="Reported number of non-detects", null=True
            ),
        ),
        migrations.AlterField(
            model_name="extractedlmrec",
            name="population_age",
            field=models.CharField(
                blank=True,
                help_text="Age groups or age ranges studied in the population",
                max_length=200,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="extractedlmrec",
            name="population_description",
            field=models.CharField(
                blank=True,
                help_text="General description of the population studied",
                max_length=200,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="extractedlmrec",
            name="population_gender",
            field=models.CharField(
                blank=True,
                choices=[("M", "Male"), ("F", "Female"), ("A", "All"), ("O", "Other")],
                help_text="Gender or genders of the population studied",
                max_length=30,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="extractedlmrec",
            name="population_other",
            field=models.CharField(
                blank=True,
                help_text="Other population information such as occupation",
                max_length=200,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="extractedlmrec",
            name="sampling_date",
            field=models.DateField(
                blank=True,
                help_text="Date or date range when the study was performed",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="extractedlmrec",
            name="sampling_method",
            field=models.CharField(
                blank=True,
                help_text="Reported method by which the media samples were collected",
                max_length=200,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="extractedlmrec",
            name="study_location",
            field=models.CharField(
                blank=True,
                help_text="Location where the study was performed",
                max_length=200,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="rawchem",
            name="chem_detected_flag",
            field=models.CharField(
                blank=True,
                choices=[("1", "Yes"), ("0", "No")],
                help_text="Flag indicating whether a chemical was ever detected in the studied medium",
                max_length=1,
                null=True,
                verbose_name="Chemical Detected",
            ),
        ),
        migrations.AlterField(
            model_name="rawchem",
            name="raw_cas",
            field=models.CharField(
                blank=True,
                help_text="Chemical abstract service registry number (CASRN) as reported in original study",
                max_length=100,
                verbose_name="Raw CAS",
            ),
        ),
        migrations.AlterField(
            model_name="rawchem",
            name="raw_chem_name",
            field=models.CharField(
                blank=True,
                help_text="Chemical name as reported in original study",
                max_length=1300,
                verbose_name="Raw chemical name",
            ),
        ),
        migrations.AlterField(
            model_name="extractedlmdoc",
            name="extraction_wa",
            field=models.TextField(
                blank=True,
                help_text="Contains details of the contract and work assignment under which data was extracted",
                verbose_name="Extraction WA",
            ),
        ),
        migrations.AlterField(
            model_name="extractedlmdoc",
            name="media",
            field=models.CharField(
                blank=True,
                help_text="General list of environmental or biological media studied",
                max_length=100,
                verbose_name="Media",
            ),
        ),
        migrations.AlterField(
            model_name="extractedlmdoc",
            name="qa_flag",
            field=models.CharField(
                blank=True,
                help_text="Indicates whether QA has been completed",
                max_length=30,
                verbose_name="QA flag",
            ),
        ),
        migrations.AlterField(
            model_name="extractedlmdoc",
            name="study_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("Targeted", "Targeted"),
                    ("Non-Targeted", "Non-Targeted or Suspect Screening"),
                    ("Other", "Other"),
                ],
                help_text="Indicates whether the study was a targeted analysis of specific chemicals, general chemical screening, or other",
                max_length=12,
                verbose_name="Study Type",
            ),
        ),
        migrations.AlterField(
            model_name="extractedtext",
            name="doc_date",
            field=models.CharField(
                blank=True,
                help_text="Date the study document was published",
                max_length=25,
                verbose_name="Document date",
            ),
        ),
    ]
