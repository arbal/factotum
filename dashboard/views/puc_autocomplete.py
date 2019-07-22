from dal import autocomplete
from dashboard.models import PUC
from django.db.models import Q


class PUCAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = PUC.objects.all()
        if self.q:
            cats = Q(gen_cat__icontains=self.q)
            fams = Q(prod_fam__icontains=self.q)
            types = Q(prod_type__icontains=self.q)
            qs = qs.filter(cats | fams | types)

        return qs
