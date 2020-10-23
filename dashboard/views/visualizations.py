from django.views import View

from dashboard.models import PUC
from django.db.models import (
    Value,
    Case,
    When,
    IntegerField,
)
from django.http import JsonResponse
from django.shortcuts import render


class Visualizations(View):
    """
    The basic GET version of the view
    """

    template_name = "visualizations/visualizations.html"

    def get(self, request):
        context = {}
        pucs = PUC.objects.with_num_products().filter(kind__code="FO").all().astree()
        for puc_name, puc_obj in pucs.items():
            puc_obj.cumulative_products = sum(
                p.num_products for p in pucs.objects[puc_name].values()
            )
        context["formulation_pucs"] = pucs

        pucs = PUC.objects.with_num_products().filter(kind__code="AR").all().astree()
        for puc_name, puc_obj in pucs.items():
            puc_obj.cumulative_products = sum(
                p.num_products for p in pucs.objects[puc_name].values()
            )
        context["article_pucs"] = pucs

        pucs = PUC.objects.filter(kind__code="OC").with_num_products().all().astree()
        for puc_name, puc_obj in pucs.items():
            puc_obj.cumulative_products = sum(
                p.num_products for p in pucs.objects[puc_name].values()
            )
        context["occupation_pucs"] = pucs
        return render(request, self.template_name, context)


def bubble_PUCs(request):
    """This view is used to download all of the PUCs in nested JSON form.
    """
    dtxsid = request.GET.get("dtxsid", None)
    kind = request.GET.get("kind", "FO")
    if dtxsid:
        pucs = PUC.objects.dtxsid_filter(dtxsid)
    else:
        pucs = PUC.objects.all()
    level = Case(
        When(prod_fam="", prod_type="", then=Value(1)),
        When(prod_fam__ne="", prod_type="", then=Value(2)),
        default=Value(3),
        output_field=IntegerField(),
        )
    pucs = pucs.filter(kind__code=kind)\
        .with_num_products()\
        .filter(num_products__gt=0)\
        .annotate(level=level)

    # convert the pucs to a simpletree
    pucs = pucs.values(
        "id", "gen_cat", "prod_fam", "prod_type", "num_products", "level"
    ).astree()

    return JsonResponse(pucs.asdict())


def collapsible_tree_PUCs(request):
    """This view is used to download all of the PUCs in nested JSON form.
    Regardless of if it is associated with an item
    """
    pucs = (
        PUC.objects.all()
            .filter(kind__code="FO")
            .values("id", "gen_cat", "prod_fam", "prod_type")
            .astree()
            .asdict()
    )

    # Name the first element.  Default = Root
    pucs["name"] = "Formulations"

    return JsonResponse(pucs)
