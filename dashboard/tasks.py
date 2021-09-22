import logging
import os
import zipfile
from zipfile import ZipFile

from celery.schedules import crontab
from django.apps import apps
from django.conf import settings
from django.utils.timezone import now
from djqscsv import write_csv

from dashboard.models import ExtractedComposition
from factotum.celery import app
from factotum.settings import DOWNLOADS_ROOT

logger = logging.getLogger("django")


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        crontab(*settings.PROVISIONAL_ASSIGNMENT_SCHEDULE.split(" ")),
        provisional_sid_assignment.s(),
        name="provisional_sid_assignment",
    )
    sender.add_periodic_task(
        crontab(*settings.GENERATE_BULK_DOWNLOAD_SCHEDULE.split(" ")),
        generate_bulk_download_file.s(),
        name="generate_bulk_download_csv",
    )


@app.task
def test(args):
    """This is an example task that just logs args"""
    logger.info(args)


@app.task()
def provisional_sid_assignment():
    """Takes any 'uncurated' raw chemicals and assigns them provisional dsstox ids.

    Sorts through all raw chemicals that have not been assigned a 'true chemical'
    and assigns them the same dsstox id as other chemicals with the same name and cas"""
    logger.info("Provisional curation starting")
    RawChem = apps.get_model("dashboard", "RawChem")

    initial_count = RawChem.objects.filter(dsstox__isnull=False).count()
    initial_time = now()

    for provision_kwargs in (
        RawChem.objects.filter(dsstox__isnull=True)
        .values("raw_chem_name", "raw_cas")
        .distinct()
    ):
        raw_chem_name = provision_kwargs.get("raw_chem_name", "")
        raw_cas = provision_kwargs.get("raw_cas", "")
        logger.debug(f"Provisioning Name {raw_chem_name} and CAS {raw_cas}")

        provision_dsstox_id = (
            RawChem.objects.filter(
                raw_chem_name=raw_chem_name, raw_cas=raw_cas, dsstox__isnull=False
            )
            .distinct()
            .values_list("dsstox_id", flat=True)
        )

        if len(provision_dsstox_id) == 1:
            provision_dsstox_id = provision_dsstox_id.first()
            try:
                RawChem.objects.filter(
                    raw_chem_name=raw_chem_name, raw_cas=raw_cas, dsstox__isnull=True
                ).update(dsstox_id=provision_dsstox_id, provisional=True)
            except Exception as e:
                logger.error(
                    f"{type(e).__name__} for {raw_chem_name} - {raw_cas}.",
                    exc_info=True,
                )

    final_count = RawChem.objects.filter(dsstox__isnull=False).count()

    logger.info(
        f"Provisional curation completed in {now() - initial_time}. {final_count - initial_count} associations made."
    )


@app.task()
def generate_bulk_download_file():
    logger.info("Generate composition bulk download task starting")
    # generate csv and zip file for user to download later
    chemicals = (
        ExtractedComposition.objects.all()
        .prefetch_related("weight_fraction_type", "unit_type", "product_uber_puc")
        .values(
            "extracted_text__data_document__data_group__data_source__title",
            "extracted_text__data_document__title",
            "extracted_text__data_document__subtitle",
            "extracted_text__doc_date",
            "extracted_text__data_document__product__title",
            "extracted_text__data_document__product__product_uber_puc__puc__kind__name",
            "extracted_text__data_document__product__product_uber_puc__puc__gen_cat",
            "extracted_text__data_document__product__product_uber_puc__puc__prod_fam",
            "extracted_text__data_document__product__product_uber_puc__puc__prod_type",
            "extracted_text__data_document__product__product_uber_puc__classification_method__name",
            "raw_chem_name",
            "raw_cas",
            "dsstox__sid",
            "dsstox__true_chemname",
            "dsstox__true_cas",
            "provisional",
            "raw_min_comp",
            "raw_max_comp",
            "raw_central_comp",
            "unit_type__title",
            "lower_wf_analysis",
            "upper_wf_analysis",
            "central_wf_analysis",
            "weight_fraction_type__title",
        )
        .order_by(
            "extracted_text__data_document__data_group__data_source",
            "extracted_text__data_document__title",
            "raw_chem_name",
        )
    )
    # the DOWNLOADS_ROOT folder should have been created by docker
    path = DOWNLOADS_ROOT
    if os.path.exists(path):
        os.chdir(path)
        # generate the csv file and compress it
        filename = "composition_chemicals.csv"
        zip_filename = "composition_chemicals.zip"
        with open(filename, "wb") as chem_file:
            write_csv(
                chemicals,
                chem_file,
                field_header_map={
                    "extracted_text__data_document__data_group__data_source__title": "Data Source",
                    "extracted_text__data_document__title": "Data Document Title",
                    "extracted_text__data_document__subtitle": "Data Document Subtitle",
                    "extracted_text__doc_date": "Document Date",
                    "extracted_text__data_document__product__title": "Product",
                    "extracted_text__data_document__product__product_uber_puc__puc__kind__name": "PUC Kind",
                    "extracted_text__data_document__product__product_uber_puc__puc__gen_cat": "PUC Gen Cat",
                    "extracted_text__data_document__product__product_uber_puc__puc__prod_fam": "PUC Prod Fam",
                    "extracted_text__data_document__product__product_uber_puc__puc__prod_type": "PUC Prod Type",
                    "extracted_text__data_document__product__product_uber_puc__classification_method__name": "PUC Classification Method",
                    "raw_chem_name": "Raw Chemical Name",
                    "raw_cas": "Raw CAS",
                    "dsstox__sid": "DTXSID",
                    "dsstox__true_chemname": "True Chemical Name",
                    "dsstox__true_cas": "True CAS",
                    "provisional": "Provisional",
                    "raw_min_comp": "Raw Min Comp",
                    "raw_max_comp": "Raw Max Comp",
                    "raw_central_comp": "Raw Central Comp",
                    "unit_type__title": "Unit Type",
                    "lower_wf_analysis": "Lower Weight Fraction",
                    "upper_wf_analysis": "Upper Weight Fraction",
                    "central_wf_analysis": "Central Weight Fraction",
                    "weight_fraction_type__title": "Weight Fraction Type",
                },
                field_serializer_map={
                    "provisional": (lambda f: ("Yes" if f == "1" else "No"))
                },
            )
        with ZipFile(zip_filename, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.write(filename)
        logger.info("Generate composition bulk download task done")
    else:
        logger.error(f"No directory found at {DOWNLOADS_ROOT}")
