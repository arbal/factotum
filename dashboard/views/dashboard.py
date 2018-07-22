import csv
import datetime
from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Count, F, DateField, DateTimeField
from dashboard.models import (DataGroup, DataDocument, DataSource, Product,
                                                            ProductToPUC, PUC)
from dateutil.relativedelta import relativedelta
from django.db.models.functions import Trunc

current_date = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d')
chart_start_datetime = datetime.datetime(datetime.datetime.now().year - 1, datetime.datetime.now().month + 1, 1)


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
    #TODO: This may need to be updated later to handle both manual and automatically assigned PUCs
    stats['product_with_puc_count'] = ProductToPUC.objects.filter(classification_method='MA').count()
    stats['product_with_puc_count_by_month'] = product_with_puc_count_by_month()

    return render(request, 'dashboard/index.html', stats)

def datadocument_count_by_date():
    # Datasets to populate linechart with document-upload statistics
    # Number of datadocuments, both overall and by type, that have been uploaded as of each date
    select_upload_date = {"upload_date": """date(uploaded_at)"""}
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
    document_stats = list(DataDocument.objects.filter(uploaded_at__gte=chart_start_datetime)\
        .annotate(upload_month = (Trunc('uploaded_at', 'month', output_field=DateTimeField()))) \
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
    # TODO: currently just grabs manually assigned PUCs, logic to be updated for handling Auto assigned PUCS
    product_stats = list(ProductToPUC.objects.filter(classification_method__exact='MA').filter(puc_assigned_time__gte=chart_start_datetime) \
        .annotate(puc_assigned_month = (Trunc('puc_assigned_time', 'month', output_field=DateField()))) \
        .values('puc_assigned_month') \
        .annotate(product_count = (Count('id'))) \
        .values('product_count', 'puc_assigned_month') \
        .order_by('puc_assigned_month'))

    if len(product_stats) < 12:
        for i in range(0, 12):
            chart_month = chart_start_datetime + relativedelta(months=i)
            if i + 1 > len(product_stats) or product_stats[i]['puc_assigned_month'] != chart_month:
                product_stats.insert(i, {'product_count': '0', 'puc_assigned_month': chart_month})
    return product_stats


def download_PUCs(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="PUCs.csv"'

    writer = csv.writer(response)
    writer.writerow(['gen_cat', 'prod_fam', 'prod_type', 'description', 'PUC_type'])
    for puc in PUC.objects.all():
        attr = puc.attribute if puc.attribute != None else ''
        writer.writerow([puc.gen_cat, puc.prod_fam, puc.prod_type,
                                                        puc.description, attr])

    return response
