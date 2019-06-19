from elasticsearch6 import Elasticsearch
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from factotum import settings
import json
from dashboard.models import DataDocument, ExtractedChemical


@login_required
def search_chemicals(request, template_name='search/es_chemicals.html'):
    '''
    Returns both the raw elasticsearch results and the django objects 
    '''

    q = request.GET.get('q', '')
    es = Elasticsearch([
        {'host': settings.ELASTIC_HOST, 'port': settings.ELASTIC_PORT, 'use_ssl': False},
    ])
    es_return = es.search(index='factotum_chemicals', body={
        'aggs': {
            'data_documents': {
                'terms' : {
                    'field': 'data_document_id',
                    'order': {
                        'score_sum': 'desc'
                    },
                    'size': 10
                },
                'aggs': {
                    'top_data_document': {
                        'top_hits': {
                            '_source': [
                                'data_document_id',
                                'data_document_title'
                            ],
                            'size': 1
                        }
                    },
                    'score_sum': {
                        'sum': {
                            'script': {
                                'source': '_score'
                            }
                        }
                    },
                    'num_products': {
                        'cardinality': {
                            'field': 'product_id'
                        }
                    }
                }
            },
            'pucs': {
                'terms' : {
                    'field': 'puc_id',
                    'order': {
                        'score_sum': 'desc'
                    },
                    'size': 10
                },
                'aggs': {
                    'top_puc': {
                        'top_hits': {
                            '_source': [
                                'puc_id',
                                'puc_gen_cat',
                                'puc_prod_fam',
                                'puc_prod_type'
                            ],
                            'size': 1
                        }
                    },
                    'score_sum': {
                        'sum': {
                            'script': {
                                'source': '_score'
                            }
                        }
                    },
                    'num_products': {
                        'cardinality': {
                            'field': 'product_id'
                        }
                    }
                }
            }
        },
        'query': {
            'dis_max': {
                'tie_breaker' : 0.0,
                'boost' : 1.0,
                'queries': [
                    {
                        'term': {
                            'kind': {
                                'value': 'FO',
                                'boost': 0.0
                            }
                        }
                    },
                    {
                        'wildcard': {
                            'raw_cas': {
                                'value': q.lower(),
                                'boost': 1.0
                            }
                        }
                    },
                    {
                        'wildcard': {
                            'raw_chem_name': {
                                'value': q.lower(),
                                'boost': 1.0
                            }
                        }
                    },
                    {
                        'wildcard': {
                            'true_cas': {
                                'value': q.lower(),
                                'boost': 1.0
                            }
                        }
                    },
                    {
                        'wildcard': {
                            'true_chemname': {
                                'value': q.lower(),
                                'boost': 1.0
                            }
                        }
                    },
                    {
                        'wildcard': {
                            'dtxsid': {
                                'value': q.lower(),
                                'boost': 1.0
                            }
                        }
                    }
                ]
            }
        },
        'size': 0
    })
    data_documents = []
    pucs = []
    for r in es_return["aggregations"]["data_documents"]["buckets"]:
        d = r["top_data_document"]["hits"]["hits"][0]["_source"]
        data_documents.append({
            "title": d["data_document_title"],
            "link": "/datadocument/" + str(d["data_document_id"]),
            "num_products": r["num_products"]["value"]
        })
    for r in es_return["aggregations"]["pucs"]["buckets"]:
        d = r["top_puc"]["hits"]["hits"][0]["_source"]
        pucs.append({
            "title": " / ".join([d[k] for k in ["puc_gen_cat", "puc_prod_fam", "puc_prod_type"] if d[k]]),
            "link": "/puc/" + str(d["puc_id"]),
            "num_products": r["num_products"]["value"]
        })
    results = {
        'time': es_return['took']/1000,
        'pucs': pucs,
        'data_documents': data_documents
    }
    context = {'results': results, 'q': q}
    return render(request, template_name, context)
