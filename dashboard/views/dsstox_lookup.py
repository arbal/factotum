from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404

from dashboard.models import DSSToxLookup, ProductDocument, PUC


@login_required()
def dsstox_lookup_detail(
    request, sid, template_name="chemicals/dsstox_substance_detail.html"
):
    s = get_object_or_404(DSSToxLookup, sid=sid)
    pdocs = ProductDocument.objects.from_chemical(s)
    pucs = PUC.objects.filter(products__in=pdocs.values("product")).distinct()
    return render(request, template_name, {"substance": s, "pucs": pucs})
