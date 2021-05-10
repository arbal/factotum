from django.shortcuts import render, get_object_or_404
from dashboard.models import FunctionalUseCategory


def functional_use_category_list(
    request, template_name="functional_use_category/functional_use_category_list.html"
):
    categories = FunctionalUseCategory.objects.all().values(
        "id", "title", "description"
    )
    return render(request, template_name, {"categories": list(categories)})


def functional_use_category_detail(
    request,
    pk,
    template_name="functional_use_category/functional_use_category_detail.html",
):
    functional_use_category = get_object_or_404(FunctionalUseCategory, pk=pk)
    data = {"functional_use_category": functional_use_category}
    return render(request, template_name, data)
