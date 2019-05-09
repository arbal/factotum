from dal import autocomplete
from dashboard.models import ExtractedListPresenceTag


class ListPresenceTagAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = ExtractedListPresenceTag.objects.all()
        if self.q:
            qs = qs.filter(name__istartswith=self.q)
        return qs
