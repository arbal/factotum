from django.shortcuts import render, get_object_or_404
from dashboard.models import HarmonizedMedium


def harmonized_medium_list(
    request, template_name="harmonized_medium/harmonized_medium_list.html"
):
    media = HarmonizedMedium.objects.all().values(
        "id", "name", "description"
    )
    return render(request, template_name, {"media": list(media)})