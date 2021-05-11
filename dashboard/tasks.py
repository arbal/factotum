import logging

from celery.schedules import crontab
from django.apps import apps
from django.conf import settings
from django.utils.timezone import now

from factotum.celery import app

logger = logging.getLogger("django")


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        crontab(*settings.PROVISIONAL_ASSIGNMENT_SCHEDULE.split(" ")),
        provisional_sid_assignment.s(),
        name="provisional_sid_assignment",
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

        provision_dsstox_id = RawChem.objects.filter(
            raw_chem_name=raw_chem_name, raw_cas=raw_cas, dsstox__isnull=False
        ).values_list("dsstox_id", flat=True)

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
