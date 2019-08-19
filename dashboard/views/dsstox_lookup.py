from collections import Counter

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404

from dashboard.models import DSSToxLookup, ProductDocument, PUC, ExtractedListPresence


@login_required()
def dsstox_lookup_detail(request, sid):
    s = get_object_or_404(DSSToxLookup, sid=sid)
    qs = ExtractedListPresence.objects.filter(dsstox=s)
    tagDict = dict(Counter([tuple(x.tags.all()) for x in qs]))
    pdocs = ProductDocument.objects.from_chemical(s)
    pucs = PUC.objects.filter(products__in=pdocs.values("product")).distinct()
    # context = {"substance": s, "pucs": pucs, "grouped_tags": grouped_tags}
    context = {"substance": s, "pucs": pucs, "tagDict": tagDict}
    return render(request, "chemicals/dsstox_substance_detail.html", context)
