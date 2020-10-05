from dal import autocomplete
from dashboard.models import PUC, PUCKind
from django.db.models import Q


class PUCAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if self.q:
            split_q = self.q.split(":")
            if len(split_q) > 1:
                puckind = Q(kind__name__istartswith=split_q[0])
                puc = split_q[1]
            else:
                puckind = Q()
                puc = split_q[0]
            return PUC.objects.filter(
                puckind,
                Q(gen_cat__icontains=puc)
                | Q(prod_fam__icontains=puc)
                | Q(prod_type__icontains=puc),
            )
        return None

    def get_result_label(self, result):
        return result.kind.code + ": " + result.__str__()
