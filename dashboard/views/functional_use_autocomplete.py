from dal import autocomplete

from dashboard.models import FunctionalUse


class FunctionalUseAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = FunctionalUse.objects.all()
        if self.q:
            qs = qs.filter(report_funcuse__contains=self.q)
        return qs
