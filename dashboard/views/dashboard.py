import csv
import datetime
from dateutil.relativedelta import relativedelta

from django.http import HttpResponse
from django.shortcuts import render
from django.db.models import Count, F, DateField, DateTimeField
from django.db.models.functions import Trunc
from django.contrib.auth.decorators import login_required

from dashboard.models import *

from dashboard.models import *

current_date = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d')
chart_start_datetime = datetime.datetime(datetime.datetime.now().year - 1, min(12,datetime.datetime.now().month + 1), 1)


def index(request):
    stats = {}
    stats['datagroup_count'] = DataGroup.objects.count()
    stats['datasource_count'] = DataSource.objects.count()

    stats['datadocument_count'] = DataDocument.objects.count()
    stats['datadocument_with_extracted_text_percent'] =\
        DataDocument.objects.filter(extracted = True).count()/DataDocument.objects.count()*100
    stats['datadocument_count_by_date'] = datadocument_count_by_date()
    stats['datadocument_count_by_month'] = datadocument_count_by_month()
    stats['product_count'] = Product.objects.count()
    stats['dss_tox_count'] = DSSToxLookup.objects.count()
    stats['chemical_count'] = ExtractedChemical.objects.count()
    stats['product_with_puc_count'] = ProductToPUC.objects.values('product_id').distinct().count()
    stats['product_with_puc_count_by_month'] = product_with_puc_count_by_month()
    return render(request, 'dashboard/index.html', stats)


def datadocument_count_by_date():
    # Datasets to populate linechart with document-upload statistics
    # Number of datadocuments, both overall and by type, that have been uploaded as of each date
    select_upload_date = {"upload_date": """date(dashboard_datadocument.created_at)"""}
    document_stats = {}
    document_stats['all'] = list(DataDocument.objects.extra(select=select_upload_date) \
                                 .values('upload_date') \
                                 .annotate(document_count = Count('id')) \
                                 .order_by('upload_date'))
    document_stats_by_type = DataDocument.objects.extra(select=select_upload_date) \
        .values('upload_date') \
        .annotate(source_type = F('document_type__title'), document_count = Count('id')) \
        .order_by('upload_date')
    document_stats['product'] = list(document_stats_by_type.filter(source_type = 'product'))
    document_stats['msds_sds'] = list(document_stats_by_type.filter(source_type = 'msds/sds'))
    for type in {'all'}:
        document_count = 0
        for item in document_stats[type]:
            if isinstance(item['upload_date'], datetime.date):
                item['upload_date'] = datetime.date.strftime((item['upload_date']), '%Y-%m-%d')
            document_count += item['document_count']
            item['document_count'] = document_count
        # if final record isn't for current date, create one
        for item in document_stats[type][len(document_stats[type])-1:]:
            if item['upload_date'] != current_date:
                document_stats[type].append({'upload_date': current_date
                                                , 'document_count': document_count})
    return document_stats


def datadocument_count_by_month():
    # GROUP BY issue solved with https://stackoverflow.com/questions/8746014/django-group-by-date-day-month-year
    document_stats = list(DataDocument.objects.filter(created_at__gte=chart_start_datetime)\
        .annotate(upload_month = (Trunc('created_at', 'month', output_field=DateTimeField()))) \
        .values('upload_month') \
        .annotate(document_count = (Count('id'))) \
        .values('document_count', 'upload_month') \
        .order_by('upload_month'))
    if len(document_stats) < 12:
        for i in range(0, 12):
            chart_month = chart_start_datetime + relativedelta(months=i)
            if i + 1 > len(document_stats) or document_stats[i]['upload_month'] != chart_month:
                document_stats.insert(i, {'document_count': '0', 'upload_month': chart_month})
    return document_stats


def product_with_puc_count_by_month():
    # GROUP BY issue solved with https://stackoverflow.com/questions/8746014/django-group-by-date-day-month-year

    product_stats = list(ProductToPUC.objects
        .filter(created_at__gte=chart_start_datetime)
        .annotate(
            puc_assigned_month = (Trunc('created_at', 'month', output_field=DateField()))
        )
        .values('puc_assigned_month')
        .annotate(product_count=Count('product', distinct=True))
        .order_by('puc_assigned_month')
        )

    if len(product_stats) < 12:
        for i in range(0, 12):
            chart_month = chart_start_datetime + relativedelta(months=i)
            if i + 1 > len(product_stats) or product_stats[i]['puc_assigned_month'] != chart_month:
                product_stats.insert(i, {'product_count': '0', 'puc_assigned_month': chart_month})
    return product_stats


def download_PUCs(request):
    '''This view gets called every time we call the index view and is used to
    populate the bubble plot. It is also used to download all of the PUCs in 
    csv form. The "bubbles" parameter in the request will either be "True" or 
    "None", it's worth noting that if when making the call to here from the 
    index page we were to use ?bubbles=False it would also give us the filtered
    PUCs because the if expression is just checking whether that parameter is 
    there.
    '''
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="PUCs.csv"'
    bubbles = request.GET.get('bubbles')
    writer = csv.writer(response)
    cols = ['gen_cat','prod_fam','prod_type','description','PUC_type','num_prods']
    writer.writerow(cols)
    pucs = PUC.objects.filter(kind='FO') if bubbles else PUC.objects.all()
    for puc in pucs:
        row = [ puc.gen_cat,
                puc.prod_fam, 
                puc.prod_type, 
                puc.description, 
                puc.get_level(), 
                puc.product_count
                ]
        writer.writerow(row)

    return response
