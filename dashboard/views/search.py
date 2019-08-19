import base64
from elastic.search import run_query, FACETS
import re

from django.http import JsonResponse
from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import html


@login_required()
def search_model(request, model, template_name="search/base.html"):
    page = request.GET.get("page", 1)
    encoded_q = request.GET.get("q", "")
    decoded_q = base64.b64decode(encoded_q).decode("unicode_escape")
    # Base64 decode the facets
    facets = {}
    for f in FACETS:
        if f in request.GET:
            facet_strs = []
            for s in request.GET[f].split(","):
                try:
                    facet_strs.append(base64.b64decode(s).decode("unicode_escape"))
                except:
                    pass
            if facet_strs:
                facets[f] = facet_strs
    result = run_query(decoded_q, model, size=10, facets=facets, page=page)
    context = {
        "encoded_q": encoded_q,
        "decoded_q": decoded_q,
        "result": result,
        "model": model,
        "faceted": bool(facets),
    }
    return render(request, template_name, context)
    # return JsonResponse(context)
