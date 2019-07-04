import csv
import datetime
from dateutil.relativedelta import relativedelta

from django.http import HttpResponse
from django.shortcuts import render
from django.db.models import Aggregate, Count, F, DateField, DateTimeField, Q
from django.db.models.functions import Trunc
from django.contrib.auth.decorators import login_required

from dashboard.models import *

current_date = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d')
chart_start_datetime = datetime.datetime(datetime.datetime.now().year - 1, min(12,datetime.datetime.now().month + 1), 1)


class GroupConcat(Aggregate):
    '''Allows Django to use the MySQL GROUP_CONCAT aggregation.

    Arguments:
        separator (str): the delimiter to use (default=',')

    Example:
        Pizza.objects.annotate(
            topping_str=GroupConcat(
                'toppings',
                separator=', ',
                distinct=True,
            )
        )
    '''
    function = 'GROUP_CONCAT'
    template = '%(function)s(%(distinct)s%(expressions)s SEPARATOR \'%(separator)s\')'
    allow_distinct = True
    def __init__(self, expression, separator=',', **extra):
        super().__init__(
            expression,
            separator=separator,
            **extra
        )


class SimpleTree:
    '''A simple tree data structure.
    
    Properties:
        name (str): the node name
        value (any): the root node value
        leaves (list): a list of children SimpleTree objects
    '''
    def __init__(self, name=None, value=None, leaves=[]):
        '''Initialize a SimpleTree instance.

        Arguments:
            name (str): the node name (default=None)
            value (any): the root node value (default=None)
            leaves (list): a list of children SimpleTree objects (default=[])
        '''
        self.name = name
        self.value = value
        self.leaves = leaves
    def set(self, names, value, default=None):
        '''Recursively add leaves to a SimpleTree object.

        Arguments:
            names (iter): an iterable of names to route the leaf under
            value (any): the leaf value (default=default)
            default (any): if a leaf doesn't exist upstream from the destination
                           use this value as the upstream leaf value
        '''
        root = self
        for name in names:
            try:
                leaf = next(l for l in root.leaves if l.name == name)
            except StopIteration:
                leaf = SimpleTree(name=name, value=default, leaves=[])
                root.leaves.append(leaf)
            root = leaf
        root.value = value
    def iter(self):
        '''Return an iterator than traverses the tree downward.'''
        yield self
        for leaf in self.leaves:
            yield from leaf.iter()
    def find(self, names):
        '''Breadth-first search

        Arguments:
            names (iter): an iterable containing the the names to look for

        Returns:
            a SimpleTree object
        '''
        root = self
        for name in names:
            root = next(l for l in root.leaves if l.name == name)
        return root


def index(request):
    stats = {}
    stats['datagroup_count'] = DataGroup.objects.count()
    stats['datasource_count'] = DataSource.objects.count()

    stats['datadocument_count'] = DataDocument.objects.count()
    stats['datadocument_with_extracted_text_percent'] =\
        DataDocument.objects.filter(extractedtext__isnull=False).count() / DataDocument.objects.count()*100
    stats['datadocument_count_by_date'] = datadocument_count_by_date()
    stats['datadocument_count_by_month'] = datadocument_count_by_month()
    stats['product_count'] = Product.objects.count()
    stats['dss_tox_count'] = DSSToxLookup.objects.count()
    stats['chemical_count'] = RawChem.objects.count()
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
    csv form.
    '''
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="PUCs.csv"'
    bubbles = request.GET.get('bubbles', None)
    dtxsid = request.GET.get('dtxsid', None)
    pucs = PUC.objects.all()
    if bubbles:
        pucs = pucs.filter(kind='FO')
    if dtxsid:
        pucs = pucs.filter(products__datadocument__extractedtext__rawchem__dsstox__sid=dtxsid)
    pucs = (pucs
        .annotate(
            allowed_attributes=GroupConcat(
                'tags__name',
                separator='; ',
                distinct=True,
            )
        )
        .annotate(
            assumed_attributes=GroupConcat(
                'tags__name',
                separator='; ',
                distinct=True,
                filter=Q(puctotag__assumed=True),
            )
        )
        .annotate(products_count=Count('products', distinct=True))
    ).order_by('gen_cat', 'prod_fam', 'prod_type')

    # Let's use a tree data structure to represent our PUC hierarchy
    # so we can efficiently traverse it to find cumulative product count
    puc_tree = SimpleTree(name='root', value=None, leaves=[])
    for puc in pucs:
        names = (n for n in (puc.gen_cat, puc.prod_fam, puc.prod_type) if n)
        puc_tree.set(names, puc)
    # Write CSV
    writer = csv.writer(response)

    cols = [
        'General category',
        'Product family',
        'Product type',
        'Allowed attributes',
        'Assumed attributes',
        'Description',
        'PUC type',
        'PUC level',
        'Product count',
        'Cumulative product count',
        'url',
    ]
    if not bubbles:
        cols.remove('url')
    writer.writerow(cols)
    for puc_leaf in puc_tree.iter():
        if puc_leaf.value:
            row = [
                puc_leaf.value.gen_cat,
                puc_leaf.value.prod_fam,
                puc_leaf.value.prod_type,
                puc_leaf.value.allowed_attributes,
                puc_leaf.value.assumed_attributes,
                puc_leaf.value.description,
                puc_leaf.value.kind,
                sum(1 for n in (puc_leaf.value.gen_cat, puc_leaf.value.prod_fam, puc_leaf.value.prod_type) if n),
                puc_leaf.value.products_count,
                sum(l.value.products_count for l in puc_leaf.iter() if l.value),
                puc_leaf.value.url
            ]
            if not bubbles:
                row = row[:-1]
            writer.writerow(row)

    return response

def download_LPKeywords(request):
    '''This view gets called to download all of the list presence keywords 
    and their definitions in a csv form.
    '''
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="ListPresenceKeywords.csv"'
    writer = csv.writer(response)
    cols = ['Keyword','Definition']
    writer.writerow(cols)
    LPKeywords = ExtractedListPresenceTag.objects.all()
    for keyword in LPKeywords:
        row = [ keyword.name,
                keyword.definition, 
                ]
        writer.writerow(row)

    return response
