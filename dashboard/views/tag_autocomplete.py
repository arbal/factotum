from dal import autocomplete
from django.db.models import Q

from dashboard.models import ExtractedListPresenceTag, ExtractedHabitsAndPracticesTag


class ListPresenceTagAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = ExtractedListPresenceTag.objects.all()
        if self.q:
            qs = qs.filter(name__istartswith=self.q)
        return qs


class HabitsAndPracticesTagAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        """Filters strings down by kind name or tag name. Can search both
        by separating with a colon.  Kind name must come first followed
        by tag name.

        :return: QuerySet - matching ExtractedHabitsAndPracticesTag
        """
        qs = ExtractedHabitsAndPracticesTag.objects.prefetch_related("kind").all()
        if self.q:
            split_q = self.q.replace(" ", "").split(":")
            kind = Q(kind__name__icontains=split_q[0])
            if len(split_q) > 1:
                name = Q(name__icontains=split_q[1])
                qs = qs.filter(kind, name)
            else:
                name = Q(name__icontains=split_q[0])
                qs = qs.filter(kind | name)
        return qs
