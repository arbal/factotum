from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import DetailView
from django.shortcuts import render, get_object_or_404
from dashboard.models import ExtractedListPresenceTag


def list_presence_tag_list(request, template_name="tags/tag_list.html"):
    tags = ExtractedListPresenceTag.objects.select_related("kind").all()
    data = {}
    data["tags"] = tags
    return render(request, template_name, data)


@method_decorator(login_required, name="dispatch")
class ListPresenceTagView(DetailView):
    template_name = "tags/tag_detail.html"
    model = ExtractedListPresenceTag
