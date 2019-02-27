from haystack import connections

from django.conf import settings
from django.http import JsonResponse
from haystack.inputs import Exact
from django.shortcuts import render
from django.db.models import Q
from haystack.query import SearchQuerySet

from dashboard.models import DataDocument, ExtractedChemical, DSSToxLookup, RawChem

def chem_search(request, template_name='search/chemical_search.html'):
    return render(request,
                  template_name,
                  {'results': chem_search_results(request.GET['q'])})

def chem_search_json_view(request):
    results = chem_search_results(request.GET['chemical'])
    results['matchedRecords'] = list(
        results['matchedRecords'].values('title', 'id', 'data_group_id', 'document_type_id'))
    results['probableRecords'] = list(
        results['probableRecords'].values('title', 'id', 'data_group_id', 'document_type_id'))
    return JsonResponse(results)

def chem_search_results(chemical):
    # Get matching curated records
    # print("Current Haystack connection: %s" % settings.HAYSTACK_CONN)
    # print(connections.connections_info.keys())
    # print("Calling Search for %s " % chemical)

    # The "matched" documents are the ones with curated chemicals
    sqs_matched = SearchQuerySet().models(RawChem).exclude(_missing_='sid').filter(content=chemical)
    #print(sqs_matched.__dict__)
    matched_doc_ids = list()

    # Get a list of the Data Document IDs for the results
    for matched in sqs_matched:
        matched_doc_ids.append(matched.data_document_id)
        #print(matched.sid)
        # print(matched.true_chemname)
        # print(matched.true_cas)
        # print(matched.data_document_id)

    #print("Matched Doc Ids %s " % matched_doc_ids)

    # Get hits from RawChemical records whether or not they have matched to DSSTOX
    # print("Calling Search for %s " % chemical)
    sqs_chem = SearchQuerySet().filter(content=chemical).models(RawChem)
    # print("Search called, chem result count:")
    # print(sqs_chem.count())
    probable_doc_ids = list()

    # Get a list of the Data Document IDs for the results
    for chem in sqs_chem:
        dd = chem.object.get_data_document()
        if dd:
            probable_doc_ids.append(dd.id)
        # print(exchem.id)
        # print(exchem.raw_chem_name)
        # print(exchem.raw_cas)
        # print('extracted text parent object:')
        # print(exchem.object.extracted_text)
        # print('grandparent data document object:')
        # print(exchem.object.extracted_text.data_document)
        # print(exchem.extracted_text__data_document_id)

    #print("probable Doc Ids %s " % probable_doc_ids)

    # Now retrieve the DataDocuments that match theses two sets themselves, so we have access to their other attributes

    dd_match = DataDocument.objects.filter(id__in=matched_doc_ids)
    dd_probable = DataDocument.objects.filter(Q(id__in=probable_doc_ids) & ~Q(id__in=matched_doc_ids))

    # Counts of each result set
    count_dd_probable = dd_probable.count()
    count_dd_match = dd_match.count()

    return {
            "queryString": chemical,
            "matchedDataDocuments": count_dd_match,
            "probableDataDocumentMatches": count_dd_probable,
            "matchedRecords": dd_match,
            "probableRecords": dd_probable,
        }
