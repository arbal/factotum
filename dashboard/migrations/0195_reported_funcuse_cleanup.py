from django.db import migrations
from django.db.models import Q
from django.db.models.functions import Trim

from dashboard.models import FunctionalUse, FunctionalUseToRawChem


def cleanup_reported_functional_use(apps, schema_editor):
    fus = FunctionalUse.objects.filter(~Q(report_funcuse=Trim("report_funcuse")))
    for fu in fus:
        # check if there is the same fu without spaces
        match_fu = FunctionalUse.objects.filter(
            report_funcuse=fu.report_funcuse.strip()
        ).first()
        if match_fu is None:
            # there is no matching fu, remove the spaces and save it
            fu.report_funcuse = fu.report_funcuse.strip()
            fu.save()
        else:
            links = FunctionalUseToRawChem.objects.filter(functional_use=fu)
            for link in links:
                match_link = FunctionalUseToRawChem.objects.filter(
                    functional_use=match_fu, chemical=link.chemical
                ).first()
                if match_link is None:
                    # update link to the matching fu
                    link.functional_use = match_fu
                    link.save()
                else:
                    # there is already a link to the matching fu, delete this one
                    link.delete()
            # delete the bad fu
            fu.delete()


def empty_reverse_function(apps, schema_editor):
    # The reverse function is not required
    pass


class Migration(migrations.Migration):
    dependencies = [("dashboard", "0194_models_documentation")]

    operations = [
        migrations.RunPython(
            code=cleanup_reported_functional_use,
            reverse_code=empty_reverse_function,
            atomic=True,
        )
    ]
