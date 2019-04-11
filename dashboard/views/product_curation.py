from urllib import parse

from django.urls import resolve
from django.utils import timezone, safestring
from django.shortcuts import redirect
from django.db.models import Count, Q
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.forms import ModelForm
from dashboard.models import *
from dashboard.forms import (ProductPUCForm, ProductLinkForm, 
                            BulkProductPUCForm, BulkProductTagForm, 
                            BulkPUCForm, ProductForm)
from taggit.forms import TagField
from taggit_labels.widgets import LabelWidget
from django.core.paginator import Paginator
from django.db.models import Max


class FilteredLabelWidget(LabelWidget):
    # overriding django-taggit-label function to display subset of tags
    def tag_list(self, tags):
        # must set form_instance in form __init__()
        puc = self.form_instance.instance.get_uber_puc() or None
        qs = self.model.objects.filter(content_object=puc,assumed=False)
        filtered = [unassumed.tag for unassumed in qs]
        return [(tag.name, 'selected taggit-tag' if tag.name in tags else 'taggit-tag')
                for tag in filtered]


class ProductTagForm(ModelForm):
    tags = TagField(required=False, widget=FilteredLabelWidget(model=PUCToTag))

    class Meta:
        model = Product
        fields = ['tags']

    def __init__(self, *args, **kwargs):
        super(ProductTagForm, self).__init__(*args, **kwargs)
        self.fields['tags'].widget.form_instance = self


@login_required()
def product_curation_index(request, template_name='product_curation/product_curation_index.html'):
    # List of all data sources which have had at least 1 data
    # document matched to a registered record
    data_sources = DataSource.objects.annotate(uploaded=Count('datagroup__datadocument'))\
        .filter(uploaded__gt=0)
    # A separate queryset of data sources and their related products without PUCs assigned
    # Changed in issue 232. Instead of filtering products based on their prod_cat being null,
    #   we now exclude all products that have a product_id contained in the ProductToPUC object set
    qs_no_puc = Product.objects.values('data_source').exclude(id__in=(ProductToPUC.objects.values_list('product_id', flat=True))).\
        filter(data_source__isnull=False).annotate(no_category=Count('id')).order_by('data_source')
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
    initial = {   'upc': ('stub_' + str(Product.objects.all().aggregate(Max('id'))["id__max"] + 1)),
        'document_type': doc.document_type,
           'return_url': request.META.get('HTTP_REFERER')}
    form = ProductLinkForm(initial=initial)
    # limit document type options to those matching parent datagroup group_type
    queryset = DocumentType.objects.filter(group_type=doc.data_group.group_type)
    form.fields['document_type'].queryset = queryset
    if request.method == 'POST':
        form = ProductLinkForm(request.POST or None)
        if form.is_valid():
            upc = form['upc'].value()
            title = form['title'].value()
            product, created = Product.objects.get_or_create(upc=upc,
                                                        data_source_id = ds_id)
            if created:
                product.title = title
                product.manufacturer = form['manufacturer'].value()
                product.brand_name = form['brand_name'].value()
                product.upc = form['upc'].value()
                product.size = form['size'].value()
                product.color = form['color'].value()
                product.save()
            if not ProductDocument.objects.filter(document=doc,
                                                    product=product).exists():
                p = ProductDocument(product=product, document=doc)
                p.save()
            document_type = form['document_type'].value()
            if document_type != doc.document_type: # update if user changes
                doc.document_type = DocumentType.objects.get(pk=document_type)
                doc.save()
            if 'datadocument' in form['return_url'].value():
                return redirect('data_document', pk=doc.pk)
            else:
                return redirect('link_product_list', pk=doc.data_group.pk)
        else:
            pass #form is invalid
    return render(request, template_name,{'document': doc, 'form': form})


@login_required()
def detach_puc_from_product(request, pk):
    p = Product.objects.get(pk=pk)
    pp = ProductToPUC.objects.get(product=p)
    pp.delete()
    return redirect('product_detail', pk=p.pk)


@login_required()
def bulk_assign_tag_to_products(request):
    template_name = 'product_curation/bulk_product_tag.html'
    products = {}
    msg = ''
    puc_form = BulkPUCForm(request.POST or None)
    form = BulkProductTagForm()
    if puc_form['puc'].value():
        puc = PUC.objects.get(pk = puc_form['puc'].value())
        assumed_tags = puc.get_assumed_tags()
        puc2tags = (PUCToTag.objects.filter(content_object=puc,assumed=False).
                                                values_list('tag', flat=True))
        form.fields['tag'].queryset = PUCTag.objects.filter(id__in=puc2tags)
        prod2pucs = (ProductToPUC.objects.filter(puc = puc).
                                        values_list('product_id', flat=True))
        products = Product.objects.filter(id__in=prod2pucs)
    if request.method == 'POST' and 'save' in request.POST:
        form = BulkProductTagForm(request.POST or None)
        form.fields['tag'].queryset = PUCTag.objects.filter(id__in=puc2tags)
        if form.is_valid():
            assign_tag = PUCTag.objects.filter(id=form['tag'].value())
            tags = assumed_tags | assign_tag
            product_ids = form['id_pks'].value().split(",")
            for id in product_ids:
                product = Product.objects.get(id=id)
                #add the assumed tags to the update
                for tag in tags:
                    ProductToTag.objects.update_or_create(tag=tag,
                                                        content_object=product)
            puc_form = BulkPUCForm()
            form = BulkProductTagForm()
            tag = assign_tag[0]
            msg = f'The "{tag.name}" Attribute was assigned to {len(product_ids)} Product(s).'
            if assumed_tags:
                msg += (' Along with the assumed tags: '
                            f'{" | ".join(x.name for x in assumed_tags)}')
            products = {}
    return render(request, template_name, {'products': products,
                                            'puc_form': puc_form,
                                            'form': form, 
                                            'msg': msg})


@login_required()
def bulk_assign_puc_to_product(request, template_name=('product_curation/'
                                                      'bulk_product_puc.html')):
    max_products_returned = 50
    q = safestring.mark_safe(request.GET.get('q', '')).lstrip()
    if q > '':
        p = (Product.objects
            .filter( Q(title__icontains=q) | Q(brand_name__icontains=q) )
            .exclude(id__in=(ProductToPUC.objects.values_list('product_id', flat=True))
            )[:max_products_returned])
        full_p_count = Product.objects.filter(Q(title__icontains=q) | Q(brand_name__icontains=q)).count()
    else:
        p = {}
        full_p_count = 0
    form = BulkProductPUCForm(request.POST or None)
    if form.is_valid():
        puc = PUC.objects.get(id=form['puc'].value())
        product_ids = form['id_pks'].value().split(",")
        for id in product_ids:
            product = Product.objects.get(id=id)
            ProductToPUC.objects.create(puc=puc, product=product, classification_method='MB',
                                    puc_assigned_usr=request.user)
    form['puc'].label = 'PUC to Assign to Selected Products'
    return render(request, template_name, {'products': p, 'q': q, 'form': form, 'full_p_count': full_p_count})


@login_required()
def assign_puc_to_product(request, pk, template_name=('product_curation/'
                                                      'product_puc.html')):
    p = Product.objects.get(pk=pk)
    p2p = ProductToPUC.objects.filter(classification_method='MA', product=p).first()
    form = ProductPUCForm(request.POST or None, instance=p2p)
    if form.is_valid():
        if p2p:
            p2p.save()
        else:
            puc = PUC.objects.get(id=form['puc'].value())
            p2p = ProductToPUC.objects.create(puc=puc, product=p, classification_method='MA',
                                        puc_assigned_usr=request.user)
        referer = request.POST.get('referer') if request.POST.get('referer') else 'category_assignment'
        pk = p2p.product.pk if referer == 'product_detail' else p2p.product.data_source.pk
        return redirect(referer, pk=pk)
    form.referer = resolve(parse.urlparse(request.META['HTTP_REFERER']).path).url_name\
        if 'HTTP_REFERER' in request.META else 'category_assignment'
    form.referer_pk = p.id if form.referer == 'product_detail' else p.data_source.id
    return render(request, template_name,{'product': p, 'form': form})


@login_required()
def product_detail(request, pk):
    template_name = 'product_curation/product_detail.html'
    p = get_object_or_404(Product, pk=pk, )
    tagform = ProductTagForm(request.POST or None, instance=p)
    tagform['tags'].label = ''
    puc = p.get_uber_puc()
    assumed_tags = puc.get_assumed_tags() if puc else PUCTag.objects.none()
    if tagform.is_valid():
        tagform.save()
    docs = p.datadocument_set.order_by('-created_at')
    return render(request, template_name, {'product'      : p,
                                            'puc'         : puc,
                                            'tagform'     : tagform,
                                            'docs'        : docs,
                                            'assumed_tags': assumed_tags
                                            })


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
def product_list(request):
    template_name = 'product_curation/products.html'
    products = Product.objects.all()
    data = {}
    data['products'] = products
    return render(request, template_name, data)
