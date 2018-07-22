from elasticsearch_dsl.connections import connections
from elasticsearch_dsl import DocType, Date
from elasticsearch.helpers import bulk
from elasticsearch import Elasticsearch
from dashboard.models import Product, DataDocument, ExtractedChemical
from django.http import JsonResponse
from haystack.generic_views import FacetedSearchView as BaseFacetedSearchView
from haystack.query import SearchQuerySet
from .  import FacetedProductSearchForm
from haystack import indexes

connections.create_connection()

def bulk_indexing():
    # TODO: get bulk indexing to work
    ProductIndex.init()
    es = Elasticsearch()
    bulk(client=es, actions=(b.indexing()
                             for b in Product.objects.all().iterator()))
    DataDocumentIndex.init()
    bulk(client=es, actions=(b.indexing()
                             for b in DataDocument.objects.all().iterator()))

class FacetedSearchView(BaseFacetedSearchView):
    form_class = FacetedProductSearchForm
    facet_fields = ['prod_cat', 'brand_name', 'facet_model_name']
    template_name = 'search/facet_search.html'
    paginate_by = 20
    context_object_name = 'object_list'

