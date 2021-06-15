from django_db_views.db_view import DBView
from django.db import models


class DuplicateChemicals(DBView):
    """
    The DuplicateChemicals view identifies all the instances where a curated
    chemical appears more than once in a single Component.
    """

    extracted_text = models.ForeignKey(
        "ExtractedText", on_delete=models.DO_NOTHING, null=False, blank=False
    )
    dsstox = models.ForeignKey(
        "DSSToxLookup", on_delete=models.DO_NOTHING, null=False, blank=False
    )
    component = models.CharField("Component", max_length=200, blank=True)

    view_definition = """
            select distinct extracted_text_id, dsstox_id, component
            from dashboard_rawchem
            where dsstox_id is not null
            group by extracted_text_id, dsstox_id, component
            having count(extracted_text_id) > 1
      """

    class Meta:
        managed = False
        db_table = "duplicate_chemicals"
