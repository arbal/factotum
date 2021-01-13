from django.views.generic import DetailView
from django.shortcuts import render
from dashboard.models import ExtractedListPresenceTag


def list_presence_tag_list(request, template_name="tags/tag_list.html"):
    tags = (
        ExtractedListPresenceTag.objects.all()
        .select_related("kind")
        .values("kind__name", "name", "definition", "id")
    )
    data = {"tags": list(tags)}
    return render(request, template_name, data)


class ListPresenceTagView(DetailView):
    template_name = "tags/tag_detail.html"
    model = ExtractedListPresenceTag
