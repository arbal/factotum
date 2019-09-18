from collections import Counter

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404

from dashboard.utils import SimpleTree, accumulate_pucs
from dashboard.models import DSSToxLookup, ProductDocument, PUC, ExtractedListPresence


@login_required()
def dsstox_lookup_detail(request, sid):
    s = get_object_or_404(DSSToxLookup, sid=sid)
    qs = ExtractedListPresence.objects.filter(dsstox=s)
    tagDict = dict(Counter([tuple(x.tags.all()) for x in qs if x.tags.exists()]))
    pdocs = ProductDocument.objects.from_chemical(s)
    all_pucs = accumulate_pucs(
        PUC.objects.filter(products__in=pdocs.values("product")).distinct()
    )
    pucs = SimpleTree(name="root", value=None, leaves=[])
    for puc in all_pucs:
        names = (n for n in (puc.gen_cat, puc.prod_fam, puc.prod_type) if n)
        pucs.set(names, puc)
    context = {"substance": s, "tagDict": tagDict, "pucs": pucs}
    return render(request, "chemicals/dsstox_substance_detail.html", context)
