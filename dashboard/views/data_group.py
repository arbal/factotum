import os
import csv
import zipfile
from itertools import islice
from collections import OrderedDict
from djqscsv import render_to_csv_response
from pathlib import Path

from django import forms
from django.urls import reverse
from django.conf import settings
from django.core.files import File
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.core.paginator import Paginator

from dashboard.models import *
from dashboard.forms import (DataGroupForm,
                             ExtractionScriptForm,
                             CleanCompDataForm,
                             create_detail_formset,
                             include_extract_form,
                             include_clean_comp_data_form)
from dashboard.utils import get_extracted_models, clean_dict, update_fields
from django.db.models import Max


@login_required()
def data_group_list(request, template_name='data_group/datagroup_list.html'):
    datagroup = DataGroup.objects.all()
    data = {}
    data['object_list'] = datagroup
    return render(request, template_name, data)

@login_required()
def data_group_detail(request, pk,
                      template_name='data_group/datagroup_detail.html'):
    dg = get_object_or_404(DataGroup, pk=pk, )
    dg.doc_types = DocumentType.objects.filter(group_type=dg.group_type)
    docs = dg.datadocument_set.get_queryset()#this needs to be updated after matching...
    prod_link = ProductDocument.objects.filter(document__in=docs)
    page = request.GET.get('page')
    paginator = Paginator(docs, 50) # TODO: make this dynamic someday in its own ticket
    store = settings.MEDIA_URL + str(dg.fs_id)
    ext = ExtractedText.objects.filter(data_document_id__in=docs).first()
    context = { 'datagroup'      : dg,
                'documents'      : paginator.page(1 if page is None else page),
                'all_documents'  : docs, # this used for template download
                'extract_fields' : dg.get_extracted_template_fieldnames(),
                'ext_err'        : {},
                'clean_comp_err'        : {},
                'extract_form'   : include_extract_form(dg),
                'clean_comp_data_form'   : include_clean_comp_data_form(dg),
                'bulk'           : len(docs) - len(prod_link),
                'msg'            : '',
                }
    if request.method == 'POST' and 'upload' in request.POST:
        # match filename to pdf name
        matched_files = [f for d in docs for f
                in request.FILES.getlist('multifiles') if f.name == d.filename]
        if not matched_files:
            context['msg'] = ('There are no matching records in the '
                                                        'selected directory.')
            return render(request, template_name, context)
        zf = zipfile.ZipFile(dg.zip_file, 'a', zipfile.ZIP_DEFLATED)
        while matched_files:
            f = matched_files.pop(0)
            doc = DataDocument.objects.get(filename=f.name,
                                            data_group=dg.pk)
            if doc.matched:
                continue
            doc.matched = True
            doc.save()
            fs = FileSystemStorage(store + '/pdf')
            afn = doc.get_abstract_filename()
            fs.save(afn, f)
            zf.write(store + '/pdf/' + afn, afn)
        zf.close()
        form = include_extract_form(dg)
        # update docs so it appears in the template table w/ "matched" docs
        context['all_documents'] = dg.datadocument_set.get_queryset()
        context['extract_form'] = form
        context['msg'] = 'Matching records uploaded successfully.'
    if request.method == 'POST' and 'extract_button' in request.POST:
        extract_form = ExtractionScriptForm(request.POST,
                                                request.FILES,dg_type=dg.type)
        if extract_form.is_valid():
            csv_file = request.FILES.get('extract_file')
            script_pk = int(request.POST['script_selection'])
            script = Script.objects.get(pk=script_pk)
            info = [x.decode('ascii','ignore') for x in csv_file.readlines()]
            table = csv.DictReader(info)
            missing =  list(set(dg.get_extracted_template_fieldnames())-
                                                        set(table.fieldnames))
            if missing: #column names are NOT a match, send back to user
                context['msg'] = ('The following columns need to be added or '
                                            f'renamed in the csv: {missing}')
                return render(request, template_name, context)
            good_records = []
            ext_parent, ext_child = get_extracted_models(dg.type)
            for i, row in enumerate(csv.DictReader(info)):
                d = docs.get(pk=int(row['data_document_id']))
                d.raw_category = row.pop('raw_category')
                wft = request.POST.get('weight_fraction_type', None)
                if wft: # this signifies 'Composition' type
                    w = 'weight_fraction_type'
                    row[w] = WeightFractionType.objects.get(pk=int(wft))
                    unit_type_id = int(row['unit_type'])
                    row['unit_type'] = UnitType.objects.get(pk=unit_type_id)
                    rank = row['ingredient_rank']
                    row['ingredient_rank'] = None if rank == '' else rank
                ext, created = ext_parent.objects.get_or_create(data_document=d,
                                                    extraction_script=script)
                if not created and ext.one_to_one_check(row):
                    # check that there is a 1:1 relation ExtParent and DataDoc
                    col = 'cat_code' if hasattr(ext,'cat_code') else 'prod_name' 
                    err_msg = ['must be 1:1 with "data_document_id".']
                    context['ext_err'][i+1] = {col: err_msg}
                if created:
                    update_fields(row, ext)
                row['extracted_text'] = ext
                if (ext_child == ExtractedListPresence):
                    row['extracted_cpcat'] = ext.extractedtext_ptr
                row = clean_dict(row, ext_child)
                try:
                    ext.full_clean()
                    ext.save()
                    record = ext_child(**row)
                    record.full_clean()
                    good_records.append((d,ext,record))
                except ValidationError as e:
                    context['ext_err'][i+1] = e.message_dict
            if context['ext_err']: # if errors, send back with errors
                [e[1].delete() for e in good_records] # delete any created exts
                return render(request, template_name, context)
            if not context['ext_err']:  # no saving until all errors are removed
                for doc,text,record in good_records:
                    doc.extracted = True
                    doc.save()
                    text.save()
                    record.save()
                fs = FileSystemStorage(store)
                fs.save(str(dg)+'_extracted.csv', csv_file)
                context['msg'] = (f'{len(good_records)} extracted records '
                                                    'uploaded successfully.')
                context['extract_form'] = include_extract_form(dg)
    if request.method == 'POST' and 'bulk' in request.POST:
        # get the set of documents that have not been matched
        a = set(docs.values_list('pk',flat=True))
        b = set(prod_link.values_list('document_id',flat=True))
        # DataDocs to make products for...
        docs_needing_products = DataDocument.objects.filter(pk__in=list(a-b))
        stub = Product.objects.all().aggregate(Max('id'))["id__max"] + 1
        for doc in docs_needing_products:
            # Try to name the new product from the ExtractedText record's prod_name
            try:
                ext = ExtractedText.objects.get(data_document_id=doc.id)
                if ext:
                    if ext.prod_name:
                        new_prod_title = ext.prod_name
                    else:
                        new_prod_title = None
            except ExtractedText.DoesNotExist:
                new_prod_title = None
            # If the ExtractedText record can't provide a title, use the DataDocument's title
            if not new_prod_title:
                if doc.title:
                    new_prod_title = '%s stub' % doc.title
                else:
                    new_prod_title = 'unknown'
            product = Product.objects.create(
                                    title=new_prod_title,
                                    upc=f'stub_{stub}',
                                    data_source_id=doc.data_group.data_source_id
                                    )
            ProductDocument.objects.create(product=product, document=doc)
            stub += 1
        context['bulk'] = 0
    if request.method == 'POST' and 'clean_comp_data_button' in request.POST:
        clean_comp_data_form = CleanCompDataForm(request.POST, request.FILES)
        if clean_comp_data_form.is_valid():
            script_pk = int(request.POST['script_selection'])
            script = Script.objects.get(pk=script_pk)
            csv_file = request.FILES.get('clean_comp_data_file')
            info = [x.decode('ascii','ignore') for x in csv_file.readlines()]
            table = csv.DictReader(info)
            missing =  list(set(dg.get_clean_comp_data_fieldnames())-
                                                        set(table.fieldnames))
            if missing: #column names are NOT a match, send back to user
                context['clean_comp_data_form'].collapsed = False
                context['msg'] = ('The following columns need to be added or '
                                            f'renamed in the csv: {missing}')
                return render(request, template_name, context)

            good_records = []
            for i, row in enumerate(csv.DictReader(info)):
                try:
                    extracted_chemical = ExtractedChemical.objects.get(rawchem_ptr=int(row['id']))
                except ExtractedChemical.DoesNotExist as e:
                    extracted_chemical = None
                    context['clean_comp_err'][i + 1] = {'id': ['No ExtractedChemical matches rawchem_ptr_id ' + row['id'], ]}
                    print('No ExtractedChemical matches rawchem_ptr_id %s' % row['id'])
                try:
                    ingredient = Ingredient.objects.get(rawchem_ptr=extracted_chemical.rawchem_ptr)
                except Ingredient.DoesNotExist as e:
                    ingredient = Ingredient(rawchem_ptr=extracted_chemical.rawchem_ptr)
                ingredient.lower_wf_analysis = row['lower_wf_analysis']
                ingredient.central_wf_analysis = row['central_wf_analysis']
                ingredient.upper_wf_analysis = row['upper_wf_analysis']
                ingredient.script = script
                try:
                    ingredient.full_clean()
                except ValidationError as e:
                    context['clean_comp_err'][i+1] = e.message_dict
                good_records.append(ingredient)
            if context['clean_comp_err']: # if errors, send back with errors
                context['clean_comp_data_form'].collapsed = False
                return render(request, template_name, context)
            if not context['clean_comp_err']:  # no saving until all errors are removed
                for ingredient in good_records:
                    ingredient.save()
                context['msg'] = (f'{len(good_records)} clean composition data records '
                                                    'uploaded successfully.')
                context['clean_comp_data_form'] = include_clean_comp_data_form(dg)
        else:
            context['clean_comp_data_form'].collapsed = False

    return render(request, template_name, context)


@login_required()
def data_group_create(request, pk,
                        template_name='data_group/datagroup_form.html'):
    datasource = get_object_or_404(DataSource, pk=pk)
    group_key = DataGroup.objects.filter(data_source=datasource).count() + 1
    default_name = '{} {}'.format(datasource.title, group_key)
    header = 'Create New Data Group For Data Source "' + str(datasource) + '"'
    initial_values = {'downloaded_by' : request.user,
                      'name'          : default_name,
                      'data_source'   : datasource}
    if request.method == 'POST':
        form = DataGroupForm(request.POST, request.FILES,
                             user    = request.user,
                             initial = initial_values)
        if form.is_valid():
            # what's the pk of the newly created datagroup?
            datagroup = form.save()
            info = [x.decode('ascii',
                             'ignore') for x in datagroup.csv.readlines()]
            table = csv.DictReader(info)
            good_fields = ['filename','title','document_type',
                                                    'url','organization']
            if not table.fieldnames == good_fields:
                datagroup.csv.close()
                datagroup.delete()
                return render(request, template_name,
                              {'field_error': table.fieldnames,
                              'good_fields': good_fields,
                               'form': form})
            text = ['DataDocument_id,' + ','.join(table.fieldnames)+'\n']
            errors = []
            filenames = []
            count = 0
            for line in table: # read every csv line, create docs for each
                count+=1
                doc_type = DocumentType.objects.get(pk=1)
                code = line['document_type']
                if line['filename'] == '' :
                    errors.append([count,"Filename can't be empty!"])
                    continue
                if len(line['filename'])>255:
                    errors.append([count,"Filename too long!"])
                    continue
                if line['filename'] in filenames:
                    errors.append([count, "Duplicate filename found in csv"])
                    continue
                if line['title'] == '': # updates title in line object
                    line['title'] = line['filename'].split('.')[0]
                if code == '':
                    errors.append([count,
                                    "'document_type' field can't be empty"])
                    continue
                if DocumentType.objects.filter(group_type=datagroup.group_type,
                                                            code=code).exists():
                    doc_type = DocumentType.objects.get(
                                    group_type=datagroup.group_type,code=code)
                else:
                    errors.append([count,"DocumentType code doesn't exist."])

                filenames.append(line['filename'])
                doc=DataDocument(filename=line['filename'],
                                 title=line['title'],
                                 document_type=doc_type,
                                 url=line['url'],
                                 organization=line['organization'],
                                 data_group=datagroup)
                doc.save()
                # update line to hold the pk for writeout
                text.append(str(doc.pk)+','+ ','.join(line.values())+'\n')
            if errors:
                datagroup.csv.close()
                datagroup.delete()
                return render(request, template_name, {'line_errors': errors,
                                                       'form': form})
            #Save the DG to make sure the pk exists
            datagroup.save()
            #Let's even write the csv first
            with open(datagroup.csv.path,'w') as f:
                myfile = File(f)
                myfile.write(''.join(text))
            #Let's explicitly use the full path for the actually writing of the zipfile
            new_zip_name = Path(settings.MEDIA_URL + "/" + str(datagroup.fs_id) + "/" + str(datagroup.fs_id) + ".zip")
            new_zip_path = Path(settings.MEDIA_ROOT + "/" + str(datagroup.fs_id) + "/" + str(datagroup.fs_id) + ".zip")
            zf = zipfile.ZipFile(str(new_zip_path), 'w',
                                 zipfile.ZIP_DEFLATED)
            datagroup.zip_file = new_zip_name
            zf.close()
            datagroup.save()
            return redirect('data_group_detail', pk=datagroup.id)
    else:
        groups = GroupType.objects.all()
        for group in groups:
            group.codes = DocumentType.objects.filter(group_type=group)
        form = DataGroupForm(user=request.user, initial=initial_values)
    context = {'form': form, 'header': header,
                'datasource': datasource, 'groups' : groups}
    return render(request, template_name, context)


@login_required()
def data_group_update(request, pk, template_name='data_group/datagroup_form.html'):
    # TODO: Resolve whether this form save ought to also update Datadocuments
    #  in the case the "Register Records CSV file" is updated.
    datagroup = get_object_or_404(DataGroup, pk=pk)
    form = DataGroupForm(request.POST or None, instance=datagroup)
    header = f'Update Data Group for Data Source "{datagroup.data_source}"'
    if form.is_valid():
        if form.has_changed():
            form.save()
        return redirect('data_group_detail', pk=datagroup.id)
    form.referer = request.META.get('HTTP_REFERER', None)
    if datagroup.extracted_docs():
        form.fields['group_type'].disabled = True
    groups = GroupType.objects.all()
    for group in groups:
            group.codes = DocumentType.objects.filter(group_type=group)
    return render(request, template_name, {'datagroup': datagroup, 
                                            'form': form,
                                            'header': header,
                                            'groups': groups})

@login_required()
def data_group_delete(request, pk, template_name='data_source/datasource_confirm_delete.html'):
    datagroup = get_object_or_404(DataGroup, pk=pk)
    if request.method == 'POST':
        datagroup.delete()
        return redirect('data_group_list')
    return render(request, template_name, {'object': datagroup})

@login_required
def dg_pdfs_zip_view(request, pk):
    dg = DataGroup.objects.get(pk=pk)
    #print('opening zip file from %s' % dg.get_zip_url())
    zip_file_name = f'{dg.fs_id}.zip'
    zip_file = open(dg.get_zip_url(), 'rb')
    response = HttpResponse(zip_file, content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename=%s' % zip_file_name
    return response

@login_required
def data_group_registered_records_csv(request, pk):
    columnlist = ['filename','title','document_type','url','organization']
    dg = DataGroup.objects.filter(pk=pk).first()
    if dg:
        columnlist.insert(0, "id")
        qs = DataDocument.objects.filter(data_group_id=pk).values(*columnlist)
        return render_to_csv_response(qs, filename=(dg.get_name_as_slug() +
                                                    "_registered_records.csv"),
                                  field_header_map={"id": "DataDocument_id"},
                                  use_verbose_names=False)
    else:
        qs = DataDocument.objects.filter(data_group_id=0).values(*columnlist)
        return render_to_csv_response(qs, filename="registered_records.csv",
                                        use_verbose_names=False)

@login_required()
def habitsandpractices(request, pk,
                      template_name='data_group/habitsandpractices.html'):
    doc = get_object_or_404(DataDocument, pk=pk, )
    script = Script.objects.get(title='Manual (dummy)', script_type='EX')
    extext, created = ExtractedText.objects.get_or_create(data_document=doc,
                                                    extraction_script=script)
    if created:
        extext.doc_date = 'please add...'
    ExtractedTextForm, HPFormSet = create_detail_formset(doc)
    # print(extext.pk)
    ext_form = ExtractedTextForm(request.POST or None, instance=extext)
    hp_formset = HPFormSet(request.POST or None, instance=extext, prefix='habits')
    context = {   'doc'         : doc,
                  'ext_form'    : ext_form,
                  'hp_formset'  : hp_formset,
                  }
    if request.method == 'POST' and 'save' in request.POST:
        if hp_formset.is_valid():
            hp_formset.save()
        if ext_form.is_valid():
            ext_form.save()
        doc.extracted = True
        doc.save()
        context = {   'doc'         : doc,
                      'ext_form'    : ext_form,
                      'hp_formset'  : hp_formset,
                      }
    return render(request, template_name, context)

@login_required
def dg_raw_extracted_records(request, pk):
    columnlist = ['extracted_text_id','id','raw_cas','raw_chem_name','raw_min_comp','raw_central_comp','raw_max_comp','unit_type__title']
    dg = DataGroup.objects.get(pk=pk)
    et = ExtractedText.objects.filter(data_document__data_group = dg).first()
    if et:
        dg_name = dg.get_name_as_slug()
        qs = ExtractedChemical.objects.filter(extracted_text__data_document__data_group_id=pk).values(*columnlist)
        #print('Writing %s records to csv' % len(qs) )
        return render_to_csv_response(qs, filename=(dg_name +
                                                    "_raw_extracted_records.csv"),
                                  field_header_map={"id": "ExtractedChemical_id"},
                                  use_verbose_names=False)
    else:
        qs = ExtractedChemical.objects.filter(extracted_text__data_document__id=pk).values(*columnlist)
        return render_to_csv_response(qs, filename='raw_extracted_records.csv' ,
                                        use_verbose_names=False)
