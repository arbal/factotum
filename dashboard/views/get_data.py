import csv
import logging
import datetime

from django.urls import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib import messages
from django.shortcuts import render
from django.db.models import Count, Q, Value, IntegerField, F
from djqscsv import render_to_csv_response

from dashboard.models import *
from dashboard.forms import HabitsPUCForm


def get_data(request, template_name="get_data/get_data.html"):
    context = {"habits_and_practices": None, "form": HabitsPUCForm(), "first": None}
    if request.method == "POST":
        form = HabitsPUCForm(request.POST)
        if form.is_valid():
            puc = PUC.objects.get(pk=form["puc"].value())
            pucs = puc.get_children()
            links = ExtractedHabitsAndPracticesToPUC.objects.filter(
                PUC__in=pucs
            ).values_list("extracted_habits_and_practices", flat=True)
            habits_and_practices = ExtractedHabitsAndPractices.objects.filter(
                pk__in=links
            )
            context["form"] = form
            context["habits_and_practices"] = habits_and_practices
            if len(habits_and_practices) > 0:
                context["first"] = habits_and_practices[0].pk
    return render(request, template_name, context)


def stats_by_dtxsids(dtxs):
    """

    Summary stats for a DTXSID

    :pucs_n: The number of unique PUCs (product categories) the chemical is associated with
    :datadocs.n: The number of data documents (e.g.  MSDS, SDS, ingredient list, product label) the chemical appears in
    :datadocs_w_wf.n: The number of data documents with associated weight fraction data that the chemical appears in (weight fraction data may be reported or predicted data, i.e., predicted from an ingredient list)
    :products.n: The number of products the chemical appears in, where a product is defined as a product entry in Factotum.
    :param dtxs: [description]
    :type dtxs: [type]
    :return: [description]
    :rtype: [type]
    """

    # The number of unique PUCs (product categories) the chemical is associated with
    pucs_n = (
        DSSToxLookup.objects.filter(sid__in=dtxs)
        .annotate(
            pucs_n=Count(
                "curated_chemical__extracted_text__data_document__product__product_uber_puc__puc",
                distinct=True,
            )
        )
        .values("sid", "pucs_n")
        .order_by()
    )

    dds_n = (
        RawChem.objects.filter(dsstox__sid__in=dtxs)
        .values("dsstox__sid")
        .annotate(sid=F("dsstox__sid"), dds_n=Count("extracted_text__data_document"))
        .values("sid", "dds_n")
        .order_by()
    )

    wf_ecs = ExtractedComposition.objects.filter(dsstox__sid__in=dtxs).exclude(
        Q(raw_max_comp="") & Q(raw_min_comp="") & Q(raw_central_comp="")
    )
    dds_wf_n = (
        DSSToxLookup.objects.filter(sid__in=dtxs)
        .filter(curated_chemical__in=wf_ecs)
        .annotate(dds_wf_n=Count("curated_chemical__extracted_text_id", distinct=True))
        .order_by()
        .values("sid", "dds_wf_n")
    )

    products_n = (
        RawChem.objects.filter(dsstox__sid__in=dtxs)
        .values("dsstox__sid")
        .annotate(products_n=Count("extracted_text__data_document__product"))
        .annotate(sid=F("dsstox__sid"))
        .values("sid", "products_n")
    )

    # build a list of stats, starting with the pucs_n object
    stats = (
        pucs_n.annotate(dds_n=Value(-1, output_field=IntegerField()))
        .annotate(dds_wf_n=Value(-1, output_field=IntegerField()))
        .annotate(products_n=Value(-1, output_field=IntegerField()))
    )

    for row in stats:
        row["dds_n"] = int(dds_n.get(sid=row["sid"])["dds_n"] or 0)

        if not dds_wf_n.filter(sid=row["sid"]):
            row["dds_wf_n"] = 0
        else:
            row["dds_wf_n"] = int(dds_wf_n.get(sid=row["sid"])["dds_wf_n"] or 0)

        row["products_n"] = int(products_n.get(sid=row["sid"])["products_n"] or 0)

    return stats


def download_chem_stats(stats):
    """[summary]

    :param stats: [description]
    :type stats: [type]
    :return: [description]
    :rtype: [type]
    """
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        'attachment; filename="chem_summary_metrics_%s.csv"'
        % (datetime.datetime.now().strftime("%Y%m%d"))
    )

    writer = csv.writer(response)
    writer.writerow(["DTXSID", "pucs_n", "dds_n", "dds_wf_n", "products_n"])
    for stat in stats:
        writer.writerow(
            [
                stat["sid"],
                stat["pucs_n"],
                stat["dds_n"],
                stat["dds_wf_n"],
                stat["products_n"],
            ]
        )

    return response


def get_data_dsstox_csv_template(request):
    response = HttpResponse(content_type="text/csv")
    response[
        "Content-Disposition"
    ] = 'attachment; filename="dsstox_lookup_template.csv"'
    writer = csv.writer(response)
    writer.writerow(["DTXSID"])
    return response


def upload_dtxsid_csv(request):
    data = {}
    if "GET" == request.method:
        return render(request, "get_data/get_data.html", data)
    try:
        csv_file = request.FILES["csv_file"]
        if not csv_file.name.endswith(".csv"):
            messages.error(request, "File is not CSV type")
            return HttpResponseRedirect(reverse("upload_dtxsid_csv"))
        # if file is too large, return
        if csv_file.multiple_chunks():
            messages.error(
                request,
                "Uploaded file is too big (%.2f MB)."
                % (csv_file.size / (1000 * 1000),),
            )
            return HttpResponseRedirect(reverse("upload_dtxsid_csv"))

        file_data = csv_file.read().decode("utf-8")

        lines = file_data.split("\n")
        dtxsids = []
        for line in lines:
            if DSSToxLookup.objects.filter(sid=str.strip(line)).count() > 0:
                dtxsids.append(
                    str.strip(line)
                )  # only add DTXSIDs that appear in the database

    except Exception as e:
        logging.getLogger("error_logger").error("Unable to upload file. " + repr(e))
        messages.error(request, "Unable to upload file. " + repr(e))

    stats = stats_by_dtxsids(dtxsids)
    # stats  = {'pucs_n': 0, 'dds_n': 0, 'dds_wf_n': 0, 'products_n': 0}
    resp = download_chem_stats(stats)
    return resp


def download_PUCTags(request):
    """respond with a CSV of PUCTags, name and definition
    """
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="PUCTags.csv"'
    writer = csv.writer(response)
    cols = ["Name", "Definition"]
    writer.writerow(cols)
    tags = PUCTag.objects.all()
    for tag in tags:
        row = [tag.name, tag.definition]
        writer.writerow(row)

    return response


def download_functional_uses(request):
    functional_uses = FunctionalUseToRawChem.objects.values(
        "chemical__extracted_text__data_document__data_group__data_source__title",
        "chemical__extracted_text__data_document__data_group__group_type__title",
        "chemical__extracted_text__data_document__title",
        "chemical__extracted_text__doc_date",
        "chemical__raw_chem_name",
        "chemical__raw_cas",
        "chemical__dsstox__sid",
        "chemical__dsstox__true_chemname",
        "chemical__dsstox__true_cas",
        "chemical__provisional",
        "functional_use__report_funcuse",
        "functional_use__category__title",
    ).order_by(
        "chemical__extracted_text__data_document__data_group__data_source__title"
    )
    filename = "functional_uses.csv"
    return render_to_csv_response(
        functional_uses,
        filename=filename,
        append_datestamp=True,
        use_verbose_names=False,
        streaming=True,
        field_header_map={
            "chemical__extracted_text__data_document__data_group__data_source__title": "Data Source",
            "chemical__extracted_text__data_document__data_group__group_type__title": "Data Type",
            "chemical__extracted_text__data_document__title": "Data Document",
            "chemical__extracted_text__doc_date": "Document Date",
            "chemical__raw_chem_name": "Raw Chemical Name",
            "chemical__raw_cas": "Raw CAS",
            "chemical__dsstox__sid": "DTXSID",
            "chemical__dsstox__true_chemname": "Curated Chemical Name",
            "chemical__dsstox__true_cas": "Curated CAS",
            "chemical__provisional": "Provisional",
            "functional_use__report_funcuse": "Reported Functional Use",
            "functional_use__category__title": "Harmonized Functional Use",
        },
    )
