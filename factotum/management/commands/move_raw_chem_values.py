from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db import transaction
from django.db.models import Count
from dashboard.models import ExtractedChemical, ExtractedFunctionalUse, ExtractedListPresence, RawChem

class Command(BaseCommand):
    help = """Shifts all the raw_cas and raw_chem_name values into the new RawChem base class,
            then assigns foreign key values to the legacy tables"""

    def handle(self, *args, **options):
        with transaction.atomic():
            with connection.cursor() as cursor:
                # Create the default record in RawChem
                cursor.execute("INSERT INTO dashboard_rawchem (`id`, `raw_cas`, `raw_chem_name`) VALUES ('0', 'Undefined', 'Undefined');"),
        
                # Insert raw_cas and raw_chem_name values from all three tables into dashboard_rawchem
                cursor.execute(
                    """INSERT INTO dashboard_rawchem (raw_cas, raw_chem_name, temp_id, temp_obj_name)
                    SELECT raw_cas, raw_chem_name, id as temp_id, 'ExtractedChemical' as temp_obj_name 
                    FROM dashboard_extractedchemical
                    UNION
                    SELECT raw_cas, raw_chem_name, id as temp_id, 'ExtractedFunctionalUse' as temp_obj_name FROM 
                    dashboard_extractedfunctionaluse
                    UNION
                    SELECT raw_cas, raw_chem_name, id as temp_id, 'ExtractedListPresence' as temp_obj_name FROM 
                    dashboard_extractedlistpresence
                    ;"""
                # Join the new records to the original tables to backfill the foreign keys
                )
                print( RawChem.objects.all().values('temp_obj_name').annotate(total=Count('temp_id')).order_by('temp_obj_name'))
                cursor.execute(
                    """UPDATE dashboard_extractedchemical echem  join
                    dashboard_rawchem rchem on echem.id = rchem.temp_id and 
                    temp_obj_name = 'ExtractedChemical'
                    SET echem.rawchem_ptr_temp_id = rchem.id;"""
                )

                cursor.execute(
                    """UPDATE dashboard_extractedfunctionaluse efu  join
                    dashboard_rawchem rchem on efu.id = rchem.temp_id and 
                    temp_obj_name = 'ExtractedFunctionalUse'
                    SET efu.rawchem_ptr_temp_id = rchem.id;"""
                )

                cursor.execute(
                    """UPDATE dashboard_extractedlistpresence elp  join
                    dashboard_rawchem rchem on elp.id = rchem.temp_id and 
                    temp_obj_name = 'ExtractedListPresence'
                    SET elp.rawchem_ptr_temp_id = rchem.id;"""
                )
                print('Finished moving raw_ attributes to RawChem model')

                # Assign new RawChem ids to the temporary foreign key in DSSToxSubstance 
                cursor.execute(
                    """UPDATE dashboard_dsstoxsubstance dss  join
                    dashboard_rawchem rchem on dss.extracted_chemical_id = rchem.temp_id and 
                    temp_obj_name = 'ExtractedChemical'
                    SET dss.rawchem_ptr_temp_id = rchem.id;"""
                )
                print('Finished assigning new RawChem keys to DSSToxSubstance')

                # Assign new RawChem ids to the temporary foreign key in Ingredient 
                cursor.execute(
                    """UPDATE dashboard_ingredient ing  join
                    dashboard_rawchem rchem on ing.extracted_chemical_id = rchem.temp_id and 
                    temp_obj_name = 'ExtractedChemical'
                    SET ing.rawchem_ptr_temp_id = rchem.id;"""
                )
                print('Finished assigning new RawChem keys to Ingredient')