from django.http import JsonResponse
from dashboard.models import DataDocument, ExtractedChemical, DSSToxSubstance
from django.db.models import Q
from haystack.query import SearchQuerySet
from haystack.inputs import Exact


def chem_search(request):

    chemical = request.GET['chemical']

    # Get matching DSSTOX records
    print("Calling Search for %s " % chemical)
    sqs_dsstox = SearchQuerySet().filter(content=chemical).models(DSSToxSubstance)
    print("Search called, dsstox result count:")
    print(sqs_dsstox.count())

    dsstox_doc_ids = list()

    # Get a list of the Data Document IDs for the results
    for dsstox in sqs_dsstox:
        dsstox_doc_ids.append(dsstox.data_document_id)
        print(dsstox.id)
        print(dsstox.true_chemname)
        print(dsstox.true_cas)
        print(dsstox.data_document_id)

    print("DSSTox Doc Ids %s " % dsstox_doc_ids)

    # Get matching Extracted Chemical records
    print("Calling Search for %s " % chemical)
    sqs_exchem = SearchQuerySet().filter(content=chemical).models(ExtractedChemical)
    print("Search called, exchem result count:")
    print(sqs_exchem.count())

    exchem_doc_ids = list()

    # Get a list of the Data Document IDs for the results
    for exchem in sqs_exchem:
        exchem_doc_ids.append(exchem.object.extracted_text.data_document.id)
        print(exchem.id)
        print(exchem.raw_chem_name)
        print(exchem.raw_cas)
        print('extracted text parent object:')
        print(exchem.object.extracted_text)
        print('grandparent data document object:')
        print(exchem.object.extracted_text.data_document)
        print(exchem.extracted_text__data_document_id)

    print("Exchem Doc Ids %s " % exchem_doc_ids)

    # Now retrieve the DataDocuments that match theses two sets themselves, so we have access to their other attributes
    dd_match = DataDocument.objects.filter(id__in=dsstox_doc_ids)
    dd_probable = DataDocument.objects.filter(Q(id__in=exchem_doc_ids) & ~Q(id__in=dsstox_doc_ids))

    # These lines below use Django object filtering instead of elastic.
    #dd_match = DataDocument.objects.filter(Q(extractedtext__extractedchemical__dsstoxsubstance__true_chemname__icontains=chemical) |
    #                                      Q(extractedtext__extractedchemical__dsstoxsubstance__true_cas__icontains=chemical))

    # dd_probable = dd_all.difference(dd_match) # Not supported by MySQL!!!

    #dd_probable = DataDocument.objects.filter(Q(extractedtext__extractedchemical__raw_chem_name__icontains=chemical) |
    #                                         Q(extractedtext__extractedchemical__raw_cas__icontains=chemical)
    #                                         ).exclude(id__in=dd_match)

    # Counts of each result set
    count_dd_probable = dd_probable.count()
    count_dd_match = dd_match.count()

    # Now we serialize the results so we can spit out the JSON
    columns = ['title', 'id', 'data_group_id', 'document_type_id']
    matched_objects = []
    for i in dd_match.values():
        ret = [i[j] for j in columns]
        matched_objects.append(ret)

    probable_objects = []
    for i in dd_probable.values():
        ret = [i[j] for j in columns]
        probable_objects.append(ret)


    # Return the JSON
    return JsonResponse({
        "Matched Data Documents": count_dd_match,
        "Probable Data Document matches": count_dd_probable,
        "Matched Records": matched_objects,
        "Probable Records": probable_objects,
    })
