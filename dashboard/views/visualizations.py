from django.views import View
from cacheops import cached, cached_view

from dashboard.models import (
    PUC,
    CumulativeProductsPerPuc,
    CumulativeProductsPerPucAndSid,
    DSSToxLookup,
)
from django.db.models import Value, Case, When, IntegerField, F
from django.http import JsonResponse
from django.shortcuts import render


class Visualizations(View):
    """
    The basic GET version of the view
    """

    template_name = "visualizations/visualizations.html"

    def get(self, request):
        context = {}
        pucs = (
            CumulativeProductsPerPuc.objects.filter(puc__kind__code="FO")
            .filter(cumulative_product_count__gt=0)
            .select_related("puc")
            .astree()
        )
        context["formulation_pucs"] = pucs

        pucs = (
            CumulativeProductsPerPuc.objects.filter(puc__kind__code="AR")
            .filter(cumulative_product_count__gt=0)
            .select_related("puc")
            .astree()
        )
        context["article_pucs"] = pucs

        pucs = (
            CumulativeProductsPerPuc.objects.filter(puc__kind__code="OC")
            .filter(cumulative_product_count__gt=0)
            .select_related("puc")
            .astree()
        )
        context["occupation_pucs"] = pucs
        return render(request, self.template_name, context)


@cached_view(timeout=60)
def bubble_PUCs(request):
    """This view is used to download all of the PUCs in nested JSON form.
    """
    dtxsid = request.GET.get("dtxsid", None)
    kind = request.GET.get("kind", "FO")
    if dtxsid:
        # avoid joining in the subsequent queryset by looking up the pk once
        dss_pk = DSSToxLookup.objects.filter(sid=dtxsid).first().pk
        # filter by products by a related DSSTOX
        if kind:
            pucs = (
                CumulativeProductsPerPucAndSid.objects.filter(dsstoxlookup_id=dss_pk)
                .filter(puc__kind__code=kind)
                .filter(cumulative_product_count__gt=0)
                .select_related("puc")
            )
        else:
            pucs = (
                CumulativeProductsPerPuc.objects.filter(dsstoxlookup_id=dss_pk)
                .filter(cumulative_product_count__gt=0)
                .select_related("puc")
            )

        pucs = (
            pucs.annotate(
                kind_id=F("puc__kind_id"),
                gen_cat=F("puc__gen_cat"),
                prod_fam=F("puc__prod_fam"),
                prod_type=F("puc__prod_type"),
            )  # change the nested __puc field names
            .values(
                "kind_id",
                "puc_id",
                "gen_cat",
                "prod_fam",
                "prod_type",
                "product_count",
                "cumulative_product_count",
                "puc_level",
            )
            .flatdictastree()
        )
    else:
        if kind:
            pucs = (
                CumulativeProductsPerPuc.objects.filter(puc__kind__code=kind)
                .filter(cumulative_product_count__gt=0)
                .select_related("puc")
            )
        else:
            pucs = CumulativeProductsPerPuc.objects.filter(
                cumulative_product_count__gt=0
            ).select_related("puc")

        pucs = (
            pucs.annotate(
                kind_id=F("puc__kind_id"),
                gen_cat=F("puc__gen_cat"),
                prod_fam=F("puc__prod_fam"),
                prod_type=F("puc__prod_type"),
            )  # change the nested __puc field names
            .values(
                "kind_id",
                "puc_id",
                "gen_cat",
                "prod_fam",
                "prod_type",
                "product_count",
                "cumulative_product_count",
                "puc_level",
            )
            .flatdictastree()
        )

    return JsonResponse(pucs.asdict())


def collapsible_tree_PUCs(request):
    """This view is used to download all of the PUCs in nested JSON form.
    Regardless of if it is associated with an item
    """
    pucs = (
        PUC.objects.all()
        .annotate(puc_id=F("id"))
        .filter(kind__code="FO")
        .values("kind_id", "puc_id", "gen_cat", "prod_fam", "prod_type")
        .astree()
        .asdict()
    )

    # Name the first element.  Default = Root
    pucs["name"] = "Formulations"

    return JsonResponse(pucs)
