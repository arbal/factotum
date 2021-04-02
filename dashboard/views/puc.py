from django.shortcuts import render, get_object_or_404
from dashboard.models import PUC, RawChem, DSSToxLookup
from django.db.models import Count, F, Q
from djqscsv import render_to_csv_response


def puc_list(request, template_name="puc/puc_list.html"):
    pucs = (
        PUC.objects.all()
        .values("kind__name", "gen_cat", "prod_fam", "prod_type", "id")
        .annotate(product_count=F("products_per_puc__product_count"))
        .order_by("kind__name", "gen_cat", "prod_fam", "prod_type")
    )
    data = {}
    data["pucs"] = list(pucs)
    return render(request, template_name, data)


def puc_detail(request, pk, template_name="puc/puc_detail.html"):
    puc = get_object_or_404(PUC, pk=pk)
    data = {"puc": puc, "linked_taxonomies": puc.get_linked_taxonomies()}
    return render(request, template_name, data)


def download_puc_chemicals(request, pk):
    puc = get_object_or_404(PUC, pk=pk)
    chemicals = DSSToxLookup.objects.filter(
        pk__in=RawChem.objects.filter(
            dsstox__isnull=False, extracted_text__data_document__products__puc=puc
        ).values("dsstox")
    ).values("sid", "true_cas", "true_chemname")

    filename = puc.__str__().replace(" ", "_") + "_chemicals.csv"
    return render_to_csv_response(
        chemicals,
        filename=filename,
        append_datestamp=True,
        field_header_map={
            "sid": "DTXSID",
            "true_chemname": "Preferred Chemical Name",
            "true_cas": "Preferred CAS",
        },
    )
