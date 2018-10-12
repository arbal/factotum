import os
import csv
import zipfile
from itertools import islice
from collections import OrderedDict
from djqscsv import render_to_csv_response
from bootstrap_datepicker_plus import DatePickerInput
from pathlib import Path

from django import forms
from django.urls import reverse
from django.conf import settings
from django.core.files import File
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.core.paginator import Paginator

from dashboard.models import *
from dashboard.utils import get_extracted_models, clean_dict, update_fields

class DataGroupForm(forms.ModelForm):
    required_css_class = 'required' # adds to label tag

    class Meta:
        model = DataGroup
        fields = ['name', 'description', 'url', 'group_type', 'downloaded_by', 'downloaded_at', 'download_script',
                  'data_source', 'csv']
        widgets = {'downloaded_at': DatePickerInput()}
        labels = {'csv': _('Register Records CSV File'),
                  'url': _('URL'), }

    def __init__(self, *args, **kwargs):
        qs = Script.objects.filter(script_type='DL')
        self.user = kwargs.pop('user', None)
        super(DataGroupForm, self).__init__(*args, **kwargs)
        self.fields['csv'].widget.attrs.update({'accept':'.csv'})
        self.fields['download_script'].queryset = qs

class ExtractionScriptForm(forms.Form):
    required_css_class = 'required' # adds to label tag
    script_selection = forms.ModelChoiceField(queryset=Script.objects.filter(script_type='EX')
                                              , label="Extraction Script")
    weight_fraction_type = forms.ModelChoiceField(queryset=WeightFractionType.objects.all()
                                                  , label="Weight Fraction Type"
                                                  , initial="1")
    extract_file = forms.FileField(label="Extracted Text CSV File")

    def __init__(self, *args, **kwargs):
        self.dg_type = kwargs.pop('dg_type', 0)
        self.user = kwargs.pop('user', None)
        super(ExtractionScriptForm, self).__init__(*args, **kwargs)
        self.fields['weight_fraction_type'].widget.attrs.update({'style':'height:2.75rem; !important'})
        self.fields['script_selection'].widget.attrs.update({'style':'height:2.75rem; !important'})
        self.fields['extract_file'].widget.attrs.update({'accept':'.csv'})
        if self.dg_type in ['Functional use','Chemical presence list']:
            del self.fields['weight_fraction_type']
        self.collapsed = True

class ExtractedTextForm(forms.ModelForm):

    class Meta:
        model = ExtractedText
        fields = ['doc_date', 'data_document', 'extraction_script']
        widgets = {
            'data_document': forms.HiddenInput(),
            'extraction_script': forms.HiddenInput(),
        }

@login_required()
def data_group_list(request, template_name='data_group/datagroup_list.html'):
    datagroup = DataGroup.objects.all()
    data = {}
    data['object_list'] = datagroup
    return render(request, template_name, data)

def include_extract_form(dg, dtype):
    '''Returns the ExtractionScriptForm based on conditions of DataGroup
    type as well as whether all records are matched, but not extracted
    '''
    if not dtype in ['Functional use','Composition', 'Chemical presence list']:
        return False
    if dg.all_matched() and not dg.all_extracted():
        return ExtractionScriptForm(dg_type=dtype)
    else:
        return False

@login_required()
def data_group_detail(request, pk,
                      template_name='data_group/datagroup_detail.html'):
    datagroup = get_object_or_404(DataGroup, pk=pk, )
    dg_type = str(datagroup.group_type)
    docs = datagroup.datadocument_set.get_queryset()#this needs to be updated after matching...
    prod_link = ProductDocument.objects.filter(document__in=docs)
    npage = 50 # TODO: make this dynamic someday in its own ticket
    page = request.GET.get('page')
    paginator = Paginator(docs, npage)
    docs_page = paginator.page(1 if page is None else page)
    store = settings.MEDIA_URL + str(datagroup.fs_id)
    extract_fields = datagroup.get_extracted_template_fieldnames()
    context = {   'datagroup'         : datagroup,
                  'documents'         : docs_page,
                  'all_documents'     : docs, # this used for template download
                  'extract_fields'    : extract_fields,
                  'ext_err'           : {},
                  'extract_form'      : include_extract_form(datagroup, dg_type),
                  'bulk'              : len(docs) - len(prod_link),
                  'msg'               : '',
                  'hnp'               : dg_type == 'Habits and Practices',
                  'composition'       : dg_type == 'Composition',
                  }
    if request.method == 'POST' and 'upload' in request.POST:
        # match filename to pdf name
        matched_files = [f for d in docs for f
                in request.FILES.getlist('multifiles') if f.name == d.filename]
        if not matched_files:
            context['msg'] = ('There are no matching records in the '
                                                        'selected directory.')
            return render(request, template_name, context)
        zf = zipfile.ZipFile(datagroup.zip_file, 'a', zipfile.ZIP_DEFLATED)
        while matched_files:
            f = matched_files.pop(0)
            doc = DataDocument.objects.get(filename=f.name,
                                            data_group=datagroup.pk)
            if doc.matched:
                continue
            doc.matched = True
            doc.save()
            fs = FileSystemStorage(store + '/pdf')
            afn = doc.get_abstract_filename()
            fs.save(afn, f)
            zf.write(store + '/pdf/' + afn, afn)
        zf.close()
        form = include_extract_form(datagroup, dg_type)
        # update docs so it appears in the template table w/ "matched" docs
        context['all_documents'] = datagroup.datadocument_set.get_queryset()
        context['extract_form'] = form
        context['msg'] = 'Matching records uploaded successfully.'
    if request.method == 'POST' and 'extract_button' in request.POST:
        extract_form = ExtractionScriptForm(request.POST,
                                                request.FILES,dg_type=dg_type)
        if extract_form.is_valid():
            csv_file = request.FILES.get('extract_file')
            script_pk = int(request.POST['script_selection'])
            script = Script.objects.get(pk=script_pk)
            info = [x.decode('ascii','ignore') for x in csv_file.readlines()]
            table = csv.DictReader(info)
            missing =  list(set(extract_fields)-set(table.fieldnames))
            if missing: #column names are NOT a match, send back to user
                context['msg'] = ('The following columns need to be added or '
                                            f'renamed in the csv: {missing}')
                return render(request, template_name, context)
            good_records = []
            ext_parent_fn, ext_child = get_extracted_models(dg_type)
            for i, row in enumerate(csv.DictReader(info)):
                doc = docs.get(pk=int(row['data_document_id']))
                doc.raw_category = row.pop('raw_category')
                wft = request.POST.get('weight_fraction_type', None)
                if wft: # this signifies 'Composition' type
                    w = 'weight_fraction_type'
                    row[w] = WeightFractionType.objects.get(pk=int(wft))
                    unit_type_id = int(row['unit_type'])
                    row['unit_type'] = UnitType.objects.get(pk=unit_type_id)
                    rank = row['ingredient_rank']
                    row['ingredient_rank'] = None if rank == '' else rank
                ext, created = ext_parent_fn(data_document=doc,
                                                extraction_script=script)
                if created:
                    update_fields(row, ext)
                row['extracted_text'] = ext
                row = clean_dict(row, ext_child)
                try:
                    ext.full_clean()
                    ext.save()
                    record = ext_child(**row)
                    record.full_clean()
                except ValidationError as e:
                    context['ext_err'][i+1] = e.message_dict
                good_records.append((doc,ext,record))
            if context['ext_err']: # if errors, send back with errors
                return render(request, template_name, context)
            if not context['ext_err']:  # no saving until all errors are removed
                for doc,text,record in good_records:
                    doc.extracted = True
                    doc.save()
                    text.save()
                    record.save()
                fs = FileSystemStorage(store)
                fs.save(str(datagroup)+'_extracted.csv', csv_file)
                context['msg'] = (f'{len(good_records)} extracted records '
                                                    'uploaded successfully.')
                context['extract_form'] = include_extract_form(datagroup,
                                                                        dg_type)
    if request.method == 'POST' and 'bulk' in request.POST:
        a = set(docs.values_list('pk',flat=True))
        b = set(prod_link.values_list('document_id',flat=True))
        # DataDocs to make products for...
        docs_needing_products = DataDocument.objects.filter(pk__in=list(a-b))
        stub = Product.objects.all().count() + 1
        for doc in docs_needing_products:
            product = Product.objects.create(
                                    title='unknown',
                                    upc=f'stub_{stub}',
                                    data_source_id=doc.data_group.data_source_id
                                    )
            ProductDocument.objects.create(product=product, document=doc)
            stub += 1
        context['bulk'] = 0
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
            count = 0
            for line in table: # read every csv line, create docs for each
                count+=1
                doc_type = DocumentType.objects.get(pk=1)
                dtype = line['document_type']
                if line['filename'] == '':
                    errors.append([count,"Filename can't be empty!"])
                if line['title'] == '': # updates title in line object
                    line['title'] = line['filename'].split('.')[0]
                if dtype == '':
                    errors.append([count,
                                    "'document_type' field can't be empty"])
                if DocumentType.objects.filter(pk=int(dtype)).exists():
                    doc_type = DocumentType.objects.get(pk=int(dtype))
                    if doc_type.group_type != datagroup.group_type:
                        errors.append([count,"Group Type doesn't match"])
                else:
                    errors.append([count,"GroupType id doesn't exist."])

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
        form = DataGroupForm(user=request.user, initial=initial_values)
    context = {'form': form, 'header': header, 'datasource': datasource}
    return render(request, template_name, context)


@login_required()
def data_group_update(request, pk, template_name='data_group/datagroup_form.html'):
    # TODO: Resolve whether this form save ought to also update Datadocuments
    #  in the case the "Register Records CSV file" is updated.
    datagroup = get_object_or_404(DataGroup, pk=pk)
    form = DataGroupForm(request.POST or None, instance=datagroup)
    header = 'Update Data Group for Data Source "' + str(datagroup.data_source) + '"'
    if form.is_valid():
        if form.has_changed():
            form.save()
        return redirect('data_group_detail', pk=datagroup.id)
    form.referer = request.META.get('HTTP_REFERER', None)
    return render(request, template_name, {'datagroup': datagroup, 'form': form, 'header': header})

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
        return render_to_csv_response(qs, filename=(dg.fs_id , "_registered_records.csv"),
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
    HPFormSet = forms.inlineformset_factory(parent_model=ExtractedText,
                                        model=ExtractedHabitsAndPractices,
                                        fields=['product_surveyed','mass',
                                                'mass_unit', 'frequency',
                                                'frequency_unit',
                                                'duration', 'duration_unit',
                                                'prevalence', 'notes'],
                                                extra=1)
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
