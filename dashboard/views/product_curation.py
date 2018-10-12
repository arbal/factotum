from dal import autocomplete
from datetime import datetime
from django.shortcuts import redirect
from django.db.models import Count, Q

from django.utils import timezone
from django import forms
from django.forms import ModelForm, ModelChoiceField
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import resolve
from urllib import parse
from dashboard.models import *
from dashboard.forms import ProductPUCForm

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

class ProductLinkForm(ModelForm):
    required_css_class = 'required' # adds to label tag
    document_type = forms.ModelChoiceField(
        queryset=DocumentType.objects.all(),
        label="Data Document Type",
        required=True)

    class Meta:
        model = Product
        fields = ['title', 'manufacturer', 'brand_name', 'upc', 'size', 'color']

class ProductForm(ModelForm):
    required_css_class = 'required' # adds to label tag

    class Meta:
        model = Product
        fields = ['title', 'manufacturer', 'brand_name', 'size', 'color', 'model_number', 'short_description',
                  'long_description']

class ProductViewForm(ProductForm):
    class Meta(ProductForm.Meta):
        exclude = ('title', 'long_description',)

    def __init__(self, *args, **kwargs):
        super(ProductForm, self).__init__(*args, **kwargs)
        for f in self.fields:
            self.fields[f].disabled = True



@login_required()
def product_curation_index(request, template_name='product_curation/product_curation_index.html'):
    # List of all data groups which have had at least 1 data
    # document matched to a registered record
    linked_products = Product.objects.filter(documents__in=DataDocument.objects.all())
    data_sources = DataSource.objects.annotate(uploaded=Count('datagroup__datadocument'))\
        .filter(uploaded__gt=0)
    # A separate queryset of data sources and their related products without PUCs assigned
    # Changed in issue 232. Instead of filtering products based on their prod_cat being null,
    #   we now exclude all products that have a product_id contained in the ProductToPUC object set
    qs_no_puc = Product.objects.values('data_source').exclude(id__in=(ProductToPUC.objects.values_list('product_id', flat=True))).\
        filter(data_source__isnull=False).annotate(no_category=Count('id')).order_by('data_source')

    #qs_no_puc = Product.objects.values('data_source').filter(prod_cat__isnull=True).\
    #    filter(data_source__isnull=False).annotate(no_category=Count('id')).order_by('data_source')
    # Convert the queryset to a list
    list_no_puc = [ds_no_puc for ds_no_puc in qs_no_puc]

    for ds in data_sources:
        try:
            ds.no_category = next((item for item in list_no_puc if item["data_source"] == ds.id), False)['no_category']
        except:
            ds.no_category = 0
        dgs = ds.datagroup_set.all()
        for dg in dgs:
            dg.unlinked = dg.datadocument_set.count() - dg.datadocument_set.filter(productdocument__document__isnull=False).count()
        ds.data_groups = dgs

    return render(request, template_name, {'data_sources': data_sources})

@login_required()
def category_assignment(request, pk, template_name=('product_curation/'
                                                'category_assignment.html')):
    """Deliver a datasource and its associated products"""
    ds = DataSource.objects.get(pk=pk)
    products = ds.source.exclude(id__in=(ProductToPUC.objects.values_list('product_id', flat=True))).order_by('-created_at')
    return render(request, template_name, {'datasource': ds, 'products': products})

@login_required()
def link_product_list(request,  pk, template_name='product_curation/link_product_list.html'):
    dg = DataGroup.objects.get(pk=pk)
    documents = dg.datadocument_set.filter(productdocument__document__isnull=True)
    npage = 20 # TODO: make this dynamic someday in its own ticket
    paginator = Paginator(documents, npage) # Show npage data documents per page
    page = request.GET.get('page')
    page = 1 if page is None else page
    docs_page = paginator.page(page)
    return render(request, template_name, {'documents':docs_page, 'datagroup':dg})

@login_required()
def link_product_form(request, pk, template_name=('product_curation/'
                                                    'link_product_form.html')):
    doc = DataDocument.objects.get(pk=pk)
    ds_id = doc.data_group.data_source_id
    upc_stub = ('stub_' + str(Product.objects.all().count() + 1))
    form = ProductLinkForm(initial={'upc': upc_stub, 'document_type': doc.document_type})
    # limit document type options to those matching parent datagroup group_type
    form.fields['document_type'].queryset =\
        form.fields['document_type'].queryset.filter(group_type_id = doc.data_group.group_type_id)
    if request.method == 'POST':
        form = ProductLinkForm(request.POST or None)
        if form.is_valid():
            title = form['title'].value()
            product, created = Product.objects.get_or_create(title=title,
                                                        data_source_id = ds_id)
            if created:
                product.manufacturer = form['manufacturer'].value()
                product.brand_name = form['brand_name'].value()
                product.upc = form['upc'].value()
                product.size = form['size'].value()
                product.color = form['color'].value()
                product.save()
            if not ProductDocument.objects.filter(document=doc).exists():
                p = ProductDocument(product=product, document=doc)
                p.save()
            document_type = form['document_type'].value()
            if document_type != doc.document_type:
                doc.document_type = DocumentType.objects.get(pk=document_type)
                doc.save()
            return redirect('link_product_list', pk=doc.data_group.pk)
    return render(request, template_name,{'document': doc, 'form': form})

@login_required()
def detach_puc_from_product(request, pk):
    p = Product.objects.get(pk=pk)
    pp = ProductToPUC.objects.get(product=p)
    pp.delete()
    return redirect('product_detail', pk=p.pk)

@login_required()
def assign_puc_to_product(request, pk, template_name=('product_curation/'
                                                      'product_puc.html')):
    """Assign a PUC to a single product"""
    form = ProductPUCForm(request.POST or None)
    p = Product.objects.get(pk=pk)
    if form.is_valid():
        puc = PUC.objects.get(id=form['puc'].value())
        # print('Selected PUC: ' + str(puc))
        producttopuc = ProductToPUC.objects.filter(product=p, classification_method='MA')
        # if product already has a puc, update it with a new puc
        if producttopuc.exists():
            # print(producttopuc)
            # print(producttopuc.get())
            producttopuc_obj = producttopuc.first()
            producttopuc_obj.PUC = puc # This assignment doesn't appear to be actually happening. . .
            producttopuc_obj.puc_assigned_time = timezone.now()
            producttopuc_obj.puc_assigned_usr = request.user
            # print('Updated ProductToPUC values:')
            # for i in producttopuc_obj._meta.get_fields():
            #     print(str(i.name) + ': ' + str(getattr(producttopuc_obj, str(i.name))))
            producttopuc_obj.save()
        else:
            ProductToPUC.objects.create(PUC=puc, product=p, classification_method='MA',
                                    puc_assigned_time=timezone.now(), puc_assigned_usr=request.user)
        referer = request.POST.get('referer') if request.POST.get('referer') else 'category_assignment'
        pk = p.id if referer == 'product_detail' else p.data_source.id
        return redirect(referer, pk=pk)
    form.referer = resolve(parse.urlparse(request.META['HTTP_REFERER']).path).url_name\
        if 'HTTP_REFERER' in request.META else 'category_assignment'
    form.referer_pk = p.id if form.referer == 'product_detail' else p.data_source.id
    return render(request, template_name,{'product': p, 'form': form})

@login_required()
def product_detail(request, pk, template_name=('product_curation/'
                                                'product_detail.html')):
    p = get_object_or_404(Product, pk=pk, )
    form = ProductViewForm(request.POST or None, instance=p)
    ptopuc = p.get_uber_product_to_puc()
    puc = p.get_uber_puc()
    return render(request, template_name, {'product': p, 'puc': puc, 'ptopuc': ptopuc, 'form': form})

@login_required()
def product_update(request, pk, template_name=('product_curation/'
                                               'product_edit.html')):
    p = Product.objects.get(pk=pk)
    form = ProductForm(request.POST or None, instance=p)
    if form.is_valid():
        form.save()
        return redirect('product_detail', pk=p.pk)
    return render(request, template_name,{'product': p, 'form': form})

@login_required()
def product_delete(request, pk):
    p = Product.objects.get(pk=pk)
    p.delete()
    return redirect('product_curation')

@login_required()
def product_list(request, template_name=('product_curation/'
                                                'products.html')):
    product = Product.objects.all()
    data = {}
    data['object_list'] = product
    return render(request, template_name, data)
