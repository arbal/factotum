from django.contrib import messages
from django.shortcuts import render, reverse, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count, F
from dashboard.models import FunctionalUse, FunctionalUseCategory
from django.http import JsonResponse
import json


@login_required()
def functional_use_curation(request):
    template_name = "functional_use_curation/functional_use_curation.html"

    combinations = (
        FunctionalUse.objects.values("report_funcuse", "category__title")
        .annotate(fu_count=Count("chemicals"))
    if request.method == "POST":
        cat = json.loads(request.POST.get("json") or "{}")
        FunctionalUse.objects.filter(report_funcuse=cat["report_funcuse"], category=cat["category"]).update(category=cat["newcategory"])
        print(cat)

        response_data = {}

        return JsonResponse(response_data)

    combinations = FunctionalUse.objects.values("report_funcuse", "category", newcategory=F("category"),
                                                categorytitle=F("category__title")) \
        .annotate(fu_count=Count("id")) \
        .order_by("report_funcuse", "category__title")

    categories = FunctionalUseCategory.objects.values("id", "title").order_by("title")
    categorylist = [{'id': '', 'title': ''}] + list(categories)

    return render(request, template_name, {"combinations": list(combinations), "categories": categorylist})
