from django.shortcuts import render, get_object_or_404
from dashboard.models import HarmonizedMedium


def harmonized_medium_list(
    request, template_name="harmonized_medium/harmonized_medium_list.html"
):
    media = HarmonizedMedium.objects.all().values("id", "name", "description")
    return render(request, template_name, {"media": list(media)})

def harmonized_medium_detail(
    request,
    pk,
    template_name="harmonized_medium/harmonized_medium_detail.html",
):
    medium = get_object_or_404(HarmonizedMedium, pk=pk)
    data = {"medium": medium}
    return render(request, template_name, data)