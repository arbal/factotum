from django.contrib import messages
from django.shortcuts import render, reverse, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count

from dashboard.models import FunctionalUse, FunctionalUseCategory


@login_required()
def functional_use_curation(request):
    template_name = "functional_use_curation/functional_use_curation.html"

    combinations = (
        FunctionalUse.objects.values("report_funcuse", "category__title")
        .annotate(fu_count=Count("chemicals"))
        .order_by("report_funcuse", "category__title")
    )
    return render(request, template_name, {"combinations": list(combinations)})
