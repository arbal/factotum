from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import DetailView

from dashboard.models import ExtractedListPresenceTag


@method_decorator(login_required, name="dispatch")
class ListPresenceTagView(DetailView):
    template_name = "tags/tag_detail.html"
    model = ExtractedListPresenceTag
