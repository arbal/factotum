import csv
import logging
import datetime

from django import forms
from django.db import connection
from django.urls import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib import messages
from django.shortcuts import render
from django.db.models import Count, Q, Value, IntegerField, Subquery, OuterRef
from django.forms.models import model_to_dict

from dashboard.models import *
from dashboard.forms import HabitsPUCForm


def get_data(request, template_name='get_data/get_data.html'):
    hnp = None
    form = HabitsPUCForm()
    context = { 'hnp' : hnp,
    'form': form,
    'first': None,
    }
    if request.method == 'POST':
        form = HabitsPUCForm(request.POST)
        if form.is_valid():
            puc_id = form['puc'].value()
            links = ExtractedHabitsAndPracticesToPUC.objects.filter(
                                            PUC_id=puc_id).values_list(
                                            'extracted_habits_and_practices',
                                            flat=True)
            hnp = ExtractedHabitsAndPractices.objects.filter(pk__in=links)
            context['form'] = form
            context['hnp'] = hnp if len(hnp)>0 else 0
            if len(hnp)>0:
                context['first'] = hnp[0].pk
    return render(request, template_name, context)


def stats_by_dtxsids(dtxs):
    """
    PUCS.n
    The number of unique PUCs (product categories) the chemical is associated with

    datadocs.n
    "The number of data documents (e.g.  MSDS, SDS, ingredient list, product label)
    the chemical is appears in"

    datadocs_w_wf.n
    "The number of data documents with associated weight fraction data
    that the chemical appears in (weight fraction data may be reported or predicted data,
     i.e., predicted from an ingredient list)"

    products.n
    "The number of products the chemical appears in, where a product is defined as a
    product entry in Factotum."
    """
    print('List of DTXSIDs provided:')
    print(dtxs)

    # pucs_n = DSSToxSubstance.objects.filter(sid__in=dtxs).distinct().\
    #     annotate(pucs_n=Count('ingredient__product__puc')).values('sid','pucs_n')
    # pucs_n = list(pucs_n)
    # TODO: Correct this to use the new model traversal after issue #340
    #pucs_n = DSSToxSubstance.objects.filter(sid__in=dtxs).distinct().\
    #    annotate(pucs_n=Count('ingredient__product__puc')).values('sid','pucs_n')
    pucs_n = DSSToxSubstance.objects.filter(sid__in=dtxs).distinct().\
        annotate(pucs_n=Count('extracted_chemical__extracted_text__data_document__product__puc')).values('sid','pucs_n')
    print('pucs_n:')
    print(pucs_n)

    # TODO: Correct this to use the new model traversal after issue #340
    #dds_n = DSSToxSubstance.objects.filter(sid__in=dtxs).distinct().\
    #    annotate(dds_n=Count('ingredient__product__datadocument')).values('sid','dds_n')
    dds_n = DSSToxSubstance.objects.filter(sid__in=dtxs).distinct().\
        annotate(dds_n=Count('extracted_chemical__extracted_text__data_document')).values('sid','dds_n')
    print('dds_n:')
    print(dds_n)

    dds_wf_n = DSSToxSubstance.objects\
    .filter(sid__in=dtxs).distinct().values('sid')\
    .annotate(
        dds_wf_n = Subquery(
            ExtractedChemical
            .objects
            .filter(pk=OuterRef('extracted_chemical_id') )
            .filter(
                Q(raw_max_comp__isnull=False) |
                Q(raw_min_comp__isnull=False) |
                Q(raw_central_comp__isnull=False)
            )
            .values('extracted_text_id')
            .annotate(dds_wf_n=Count('extracted_text_id') )
            .values('dds_wf_n')
        )
    )

    dds_wf_n = {}
    strsql = ("SELECT dss.sid , "
                "IFNULL("
                    "SUM( "
                        "(SELECT Count(DISTINCT ec2.extracted_text_id) as dd_wf_id "
                        "FROM dashboard_extractedchemical ec2 "
                        "WHERE ec2.id = dss.extracted_chemical_id "
                        "GROUP BY ec2.extracted_text_id "
                        "HAVING SUM( ( "
                            "(ec2.raw_max_comp IS NULL) +  "
                            "(ec2.raw_min_comp IS NULL) +  "
                            "(ec2.raw_central_comp IS NULL) "
                            ") = 0) > 0 )) "
                            ",0 "
                            ") as dds_wf_n "
                            "FROM dashboard_dsstoxsubstance dss "
                            "LEFT JOIN dashboard_extractedchemical ec "
                            "on ec.id = dss.extracted_chemical_id "
                            "GROUP BY dss.sid ")
    cursor_dds_wf_n = connection.cursor()
    cursor_dds_wf_n.execute(strsql)
    col_names = [desc[0] for desc in cursor_dds_wf_n.description]

    print('dds_wf_n:')
    for row in cursor_dds_wf_n:
        #print('sid: %s      dds_wf_n: %i' % (row[0], row[1]))
        if row[0] in dtxs:
            #print('adding to dds_wf_n')
            dds_wf_n[row[0]] = row[1]


    # TODO: Correct this to use the new model traversal after issue #340
    #products_n = DSSToxSubstance.objects.filter(sid__in=dtxs).distinct().\
    #   annotate(products_n=Count('ingredient__product')).values('sid', 'products_n')
    products_n = DSSToxSubstance.objects.filter(sid__in=dtxs).distinct().\
       annotate(products_n=Count('extracted_chemical__extracted_text__data_document')).values('sid', 'products_n')
    #print('products_n:')
    #print(products_n)

    stats = pucs_n\
    .annotate(dds_n=Value(-1, output_field=IntegerField())) \
    .annotate(dds_wf_n=Value(-1, output_field=IntegerField())) \
    .annotate(products_n=Value(-1, output_field=IntegerField()))

    for row in stats:
        row['dds_n'] = int(dds_n.get(sid=row['sid'])['dds_n'] or 0)
        row['dds_wf_n'] = dds_wf_n[row['sid']]
        row['products_n'] = int(products_n.get(sid=row['sid'])['products_n'] or 0)

    return stats

def download_chem_stats(stats):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="chem_summary_metrics_%s.csv"' % (datetime.datetime.now().strftime("%Y%m%d"))

    writer = csv.writer(response)
    writer.writerow(['DTXSID',  'pucs_n', 'dds_n', 'dds_wf_n', 'products_n'])
    for stat in stats:
        writer.writerow([stat['sid'], stat['pucs_n'], stat['dds_n'], stat['dds_wf_n'], stat['products_n']])

    return response

def get_data_dsstox_csv_template(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="dsstox_substance_template.csv"'
    writer = csv.writer(response)
    writer.writerow(['DTXSID'])
    return response


def upload_dtxsid_csv(request):
    data = {}
    if "GET" == request.method:
        return render(request, "get_data/get_data.html", data)
    # if not GET, then proceed
    try:
        csv_file = request.FILES["csv_file"]
        if not csv_file.name.endswith('.csv'):
            messages.error(request,'File is not CSV type')
            return HttpResponseRedirect(reverse("upload_dtxsid_csv"))
        #if file is too large, return
        if csv_file.multiple_chunks():
            messages.error(request,"Uploaded file is too big (%.2f MB)." % (csv_file.size/(1000*1000),))
            return HttpResponseRedirect(reverse("upload_dtxsid_csv"))

        file_data = csv_file.read().decode("utf-8")

        lines = file_data.split("\n")
        #loop over the lines
        dtxsids = []
        for line in lines:
            print(line)
            if DSSToxSubstance.objects.filter(sid=str.strip(line)).count() > 0:
                dtxsids.append(str.strip(line)) # only add DTXSIDs that appear in the database

    except Exception as e:
        logging.getLogger("error_logger").error("Unable to upload file. "+repr(e))
        messages.error(request,"Unable to upload file. "+repr(e))

    #TODO: Correct the stats calculations to use the new model structure created in #340
    stats = stats_by_dtxsids(dtxsids)
    #stats  = {'pucs_n': 0, 'dds_n': 0, 'dds_wf_n': 0, 'products_n': 0}
    resp = download_chem_stats(stats)
    print(resp)
    return resp
