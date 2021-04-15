from django.shortcuts import render, get_object_or_404
from dashboard.models import PUC, RawChem, DSSToxLookup, ExtractedComposition
from django.db.models import Count, F, Q
from djqscsv import render_to_csv_response


def puc_list(request, template_name="puc/puc_list.html"):
    pucs = (
        PUC.objects.all()
        .values("kind__name", "gen_cat", "prod_fam", "prod_type", "id")
        .annotate(product_count=Count("productuberpuc"))
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


def download_puc_products_weight_fractions(request, pk):
    puc = get_object_or_404(PUC, pk=pk)
    chems = (
        ExtractedComposition.objects.filter(
            extracted_text__data_document__products__product_uber_puc__puc=puc
        )
        .prefetch_related("weight_fraction_type", "unit_type")
        .values(
            "extracted_text__data_document__title",
            "extracted_text__data_document__products__title",
            "raw_chem_name",
            "raw_cas",
            "dsstox__sid",
            "dsstox__true_chemname",
            "dsstox__true_cas",
            "raw_min_comp",
            "raw_max_comp",
            "raw_central_comp",
            "unit_type__title",
            "lower_wf_analysis",
            "upper_wf_analysis",
            "central_wf_analysis",
            "weight_fraction_type__title",
        )
        .distinct()
        .order_by(
            "extracted_text__data_document__title",
            "extracted_text__data_document__products__title",
            "raw_chem_name",
        )
    )
    filename = puc.__str__().replace(" - ", "_") + "_products_and_weight_fractions.csv"
    return render_to_csv_response(
        chems,
        filename=filename,
        append_datestamp=True,
        use_verbose_names=False,
        field_header_map={
            "extracted_text__data_document__title": "Data Document",
            "extracted_text__data_document__products__title": "Product Name",
            "raw_chem_name": "Raw Chemical Name",
            "raw_cas": "Raw CAS Number",
            "dsstox__sid": "DTXSID",
            "dsstox__true_chemname": "Curated Chemical Name",
            "dsstox__true_cas": "Curated CAS Number",
            "raw_min_comp": "Raw Min Comp",
            "raw_max_comp": "Raw Max Comp",
            "raw_central_comp": "Raw Central Comp",
            "unit_type__title": "Unit Type",
            "lower_wf_analysis": "Lower Weight Fraction",
            "upper_wf_analysis": "Upper Weight Fraction",
            "central_wf_analysis": "Central Weight Fraction",
            "weight_fraction_type__title": "Weight Fraction Type",
        },
    )
