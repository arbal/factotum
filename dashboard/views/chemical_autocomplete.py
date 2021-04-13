from dal import autocomplete
from django.db.models import Q

from dashboard.models import RawChem


class ChemicalAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = RawChem.objects.all()
        if self.q:
            try:
                q_int = int(self.q)
                qs = qs.filter(Q(raw_chem_name__istartswith=self.q) | Q(pk=q_int))
            except ValueError:
                qs = qs.filter(raw_chem_name__istartswith=self.q)
        return qs
