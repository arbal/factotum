from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View

from dashboard.models import GroupType
from dashboard.views.dashboard import get_stats


class Statistics(View):
    """
    The basic GET version of the view
    """

    template_name = "statistics/statistics.html"

    def get(self, request):
        stats = get_stats()
        return render(request, self.template_name, {"stats": stats})


def grouptype_stats(request):
    """Return a json representation of the stats for GroupType.
    Returns:
    json: { "data" : [[ title, documentcount (%), rawchemcount (%), curatedchemcount (%) ], [...], ], }
    """
    grouptype_rows = GroupType.objects.annotate(
        documentcount=Count("datagroup__datadocument", distinct=True),
        rawchemcount=Count(
            "datagroup__datadocument__extractedtext__rawchem", distinct=True
        ),
        curatedchemcount=Count(
            "datagroup__datadocument__extractedtext__rawchem",
            distinct=True,
            filter=Q(
                datagroup__datadocument__extractedtext__rawchem__dsstox_id__isnull=False
            ),
        ),
    ).order_by("-documentcount")

    datadocument_total = rawchem_total = curatedchem_total = 0
    for row in grouptype_rows:
        datadocument_total += row.documentcount
        rawchem_total += row.rawchemcount
        curatedchem_total += row.curatedchemcount

    return JsonResponse(
        {
            "data": [
                [
                    row.title,
                    # Document count by grouptype with % total
                    f"{row.documentcount} ({(row.documentcount / (datadocument_total or 1))*100:.0f}%)",
                    # Raw chemical counts by grouptype with % total
                    f"{row.rawchemcount} ({(row.rawchemcount / (rawchem_total or 1))*100:.0f}%)",
                    # Curated chemical counts by grouptypes with % total
                    f"{row.curatedchemcount} ({(row.curatedchemcount / (curatedchem_total or 1))*100:.0f}%)",
                ]
                for row in grouptype_rows
            ]
        }
    )
