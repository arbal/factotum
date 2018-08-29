from dal import autocomplete
from dashboard.models import PUC
from django.db.models import Q


class PUCAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = PUC.objects.all()
        if self.q:
            qs = qs.filter(Q(gen_cat__icontains=self.q) | Q(prod_fam__icontains=self.q) | Q(prod_type__icontains=self.q))

        return qs
