from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from dashboard.models import PUC
from django.db.models import Count


def puc_list(request, template_name="puc/puc_list.html"):
    pucs = (
        PUC.objects.all()
        .values("kind__name", "gen_cat", "prod_fam", "prod_type", "id")
        .annotate(product_count=Count("products"))
        .order_by("kind__name", "gen_cat", "prod_fam", "prod_type")
    )
    data = {}
    data["pucs"] = list(pucs)
    return render(request, template_name, data)


def puc_detail(request, pk, template_name="puc/puc_detail.html"):
    puc = get_object_or_404(PUC, pk=pk)
    data = {"puc": puc, "linked_taxonomies": puc.get_linked_taxonomies()}
    return render(request, template_name, data)
