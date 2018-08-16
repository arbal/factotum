import os
import csv
import zipfile
from datetime import datetime
from itertools import islice
from collections import OrderedDict

from django import forms
from django.conf import settings
from django.core.files import File
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from bootstrap_datepicker_plus import DatePickerInput

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from djqscsv import * # whatever this is used for, it shouldn't be a star import

from dashboard.models import *


class DataGroupForm(forms.ModelForm):
    required_css_class = 'required' # adds to label tag

    class Meta:
        model = DataGroup
        fields = ['name', 'description', 'group_type', 'downloaded_by', 'downloaded_at', 'download_script', 'data_source', 'csv']
        widgets = {'downloaded_at': DatePickerInput()}
        labels = {'csv': _('Register Records CSV File'), }

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
        # print('Inside ExtractionScriptForm, kwargs:')
        # print(kwargs)
        # print('Inside ExtractionScriptForm, args:')
        # print(args)
        # print('-------------')
        self.dg_type = kwargs.pop('dg_type', 0)
        self.user = kwargs.pop('user', None)
        super(ExtractionScriptForm, self).__init__(*args, **kwargs)
        self.fields['weight_fraction_type'].widget.attrs.update({'style':'height:2.75rem; !important'})
        self.fields['script_selection'].widget.attrs.update({'style':'height:2.75rem; !important'})
        self.fields['extract_file'].widget.attrs.update({'accept':'.csv'})
        if self.dg_type in ['Functional use']:
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
    if not dtype in ['Functional use','Composition']:
        return False
    if dg.all_matched() and not dg.all_extracted():
        return ExtractionScriptForm(dg_type=dtype)
    else:
        return False

@login_required()
def data_group_detail(request, pk,
                      template_name='data_group/datagroup_detail.html'):
    datagroup = get_object_or_404(DataGroup, pk=pk, )
    dg_type = str(datagroup.group_type) # 'MSDS' #FunctionalUse
    docs = datagroup.datadocument_set.get_queryset()
    prod_link = ProductDocument.objects.filter(document__in=docs)
    npage = 50 # TODO: make this dynamic someday in its own ticket
    page = request.GET.get('page')
    paginator = Paginator(docs, npage)
    docs_page = paginator.page(1 if page is None else page)
    store = settings.MEDIA_URL + datagroup.name.replace(' ','_')
    extract_fields = ['data_document_id','data_document_filename','prod_name','doc_date','rev_num',
                      'raw_cas', 'raw_chem_name', 'report_funcuse',]
    if dg_type in ['Composition']:
        extract_fields = extract_fields + ['raw_min_comp','raw_max_comp',
                            'unit_type', 'ingredient_rank', 'raw_central_comp']
    context = {   'datagroup'         : datagroup,
                  'documents'         : docs_page,
                  'all_documents'     : docs, # this used for template download
                  'extract_fields'    : extract_fields,
                  'ext_err'           : {},
                  'upload_form'       : not datagroup.all_matched(),
                  'extract_form'      : include_extract_form(datagroup, dg_type),
                  'bulk'              : len(docs) - len(prod_link),
                  'msg'               : '',
                  'hnp'               : dg_type == 'Habits and practices',
                  'composition'       : dg_type == 'Composition',
                  }
    if request.method == 'POST' and 'upload' in request.POST:
        # match filename to pdf name
        proc_files = [f for d in docs for f
                in request.FILES.getlist('multifiles') if f.name == d.filename]
        if not proc_files:  # return render here!
            context['msg'] = ('There are no matching records in the '
                                                        'selected directory.')
            return render(request, template_name, context)
        zf = zipfile.ZipFile(datagroup.zip_file, 'a', zipfile.ZIP_DEFLATED)
        while proc_files:
            pdf = proc_files.pop(0)
            # set the Matched value of each registered record to True
            doc = DataDocument.objects.get(filename=pdf.name,
                                            data_group=datagroup.pk)
            if doc.matched:  # continue if already matched
                continue
            doc.matched = True
            doc.save()
            fs = FileSystemStorage(store + '/pdf')
            fs.save(pdf.name, pdf)
            zf.write(store + '/pdf/' + pdf.name, pdf.name)
        zf.close()
        form = include_extract_form(datagroup, dg_type)
        context['upload_form'] = not datagroup.all_matched()
        context['extract_form'] = form
        context['msg'] = 'Matching records uploaded successfully.'
    if request.method == 'POST' and 'extract_button' in request.POST:
        # print('------')
        # print('Request POST and FILE objects before being passed to ExtractionScriptForm:')
        # print(request.POST)
        # print(request.FILES)
        # print('just the extract_file object:')
        # print(request.FILES.get('extract_file'))
        # print('------')
        # extract_form.collapsed = False
        extract_form = ExtractionScriptForm(request.POST,
                                                request.FILES,dg_type=dg_type)
        wft_id = request.POST.get('weight_fraction_type',None)
        if extract_form.is_valid():
            #print('form is valid, about to handle csv file')
            csv_file = request.FILES.get('extract_file')
            # context['ext_err'][4] = {'47':'oops!'}
            script = Script.objects.get(pk=request.POST['script_selection'])
            info = [x.decode('ascii','ignore') for x in csv_file.readlines()]
            table = csv.DictReader(info)
            missing =  list(set(table.fieldnames)-set(extract_fields))
            if missing: #column names are NOT a match, send back to user
                context['msg'] = ('The following columns need to be renamed in '
                                                        f'the csv: {missing}')
                return render(request, template_name, context)
            good_records = []
            for i, row in enumerate(csv.DictReader(info)):
                text_data = OrderedDict(islice(row.items(),5))
                text_data.pop('data_document_filename') # not needed in dict
                rec_data = OrderedDict(islice(row.items(),5,
                                                        len(extract_fields)))
                dd = row['data_document_id']
                doc = get_object_or_404(docs, pk=dd)
                if ExtractedText.objects.filter(pk=dd).exists():
                    text = ExtractedText.objects.get(pk=dd)
                else:
                    text_data['extraction_script_id'] = script.id
                    text = ExtractedText(**text_data)
                rec_data['extracted_text'] = text
                if dg_type in ['Functional use']:
                    record = ExtractedFunctionalUse(**rec_data)
                if dg_type in ['Composition']:
                    rec_data['unit_type'] = UnitType.objects.get(
                                                    pk=int(row['unit_type']))
                    rec_data['weight_fraction_type_id'] = int(wft_id)
                    rank = rec_data['ingredient_rank']
                    rec_data['ingredient_rank'] = None if rank == '' else rank
                    record = ExtractedChemical(**rec_data)
                try:
                    text.full_clean()
                    text.save()
                    record.full_clean()
                except ValidationError as e:
                    context['ext_err'][i+1] = e.message_dict
                good_records.append((doc,text,record))
            if context['ext_err']: # if errors, send back with errors above <body>
                print('HIT!')
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
            product = Product.objects.create(title='unknown',
                                             upc=f'stub_{stub}',
                                             data_source_id=doc.data_group.data_source_id)
            ProductDocument.objects.create(product=product, document=doc)
            stub += 1
        context['bulk'] = 0
    return render(request, template_name, context)


@login_required()
def data_group_create(request, template_name='data_group/datagroup_form.html'):
    #if coming directly to this URL somehow, redirect
    if not(request.session.get('datasource_title') and request.session.get('datasource_pk')):
        return redirect('data_source_list')
    # get the data source from which the create button was clicked
    datasource_title = request.session['datasource_title']
    datasource_pk = request.session['datasource_pk']
    # the default name of the new data group is the name
    # of its data source, followed by the count of existing data groups + 1
    # This can result in the name defaulting to a name that already exists
    #
    group_key = DataGroup.objects.filter(data_source=datasource_pk).count() + 1
    default_name = '{} {}'.format(datasource_title, group_key)
    initial_values = {'downloaded_by' : request.user,
                      'name'          : default_name,
                      'data_source'   : datasource_pk}
    if request.method == 'POST':
        form = DataGroupForm(request.POST, request.FILES,
                             user    = request.user,
                             initial = initial_values)
        if form.is_valid():
            datagroup = form.save()
            info = [x.decode('ascii',
                             'ignore') for x in datagroup.csv.readlines()]
            table = csv.DictReader(info)
            if not table.fieldnames == ['filename','title','document_type','product','url','organization']:
                datagroup.csv.close()
                datagroup.delete()
                return render(request, template_name,
                              {'field_error': table.fieldnames,
                               'form': form})
            text = ['DataDocument_id,' + ','.join(table.fieldnames)+'\n']
            errors = []
            count = 0
            for line in table: # read every csv line, create docs for each
                count+=1
                doc_type = DocumentType.objects.get(pk=1)
                if line['filename'] == '':
                    errors.append(count)
                if line['title'] == '': # updates title in line object
                    line['title'] = line['filename'].split('.')[0]
                if line['document_type'] == '':
                    errors.append(count)
                else:
                    if DocumentType.objects.filter(pk=int(line['document_type'])).exists():
                        doc_type = DocumentType.objects.get(pk=int(line['document_type']))
                    else:
                        errors.append(count)
                doc=DataDocument(filename=line['filename'],
                                 title=line['title'],
                                 document_type=doc_type,
                                 product_category=line['product'],
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
            dg_dir = datagroup.name.replace(' ','_')
            zf = zipfile.ZipFile('media/{0}/{0}.zip'.format(dg_dir), 'w',
                                 zipfile.ZIP_DEFLATED)
            datagroup.zip_file = zf.filename
            zf.close()
            datagroup.save()
            with open(datagroup.csv.path,'w') as f:
                myfile = File(f)
                myfile.write(''.join(text))
            return redirect('data_group_detail', pk=datagroup.id)
    else:
        form = DataGroupForm(user=request.user, initial=initial_values)
    return render(request, template_name, {'form': form})


@login_required()
def data_group_update(request, pk):
    # TODO: Resolve whether this form save ought to also update Datadocuments
    #       in the case the "Register Records CSV file" is updated.
    # TODO: Shouldn't this return the user to the update form?
    datagroup = get_object_or_404(DataGroup, pk=pk)
    form = DataGroupForm(request.POST or None, instance=datagroup)
    if form.is_valid():
        form.save()
        return redirect('data_group_list')
    return render(request, 'data_group/datagroup_form.html', {'form': form})


@login_required()
def data_group_delete(request, pk, template_name='data_source/datasource_confirm_delete.html'):
    datagroup = get_object_or_404(DataGroup, pk=pk)
    if request.method == 'POST':
        datagroup.delete()
        return redirect('data_group_list')
    return render(request, template_name, {'object': datagroup})


@login_required()
def data_document_detail(request, pk,
                         template_name='data_group/data_document_detail.html'):
    doc = get_object_or_404(DataDocument, pk=pk, )
    return render(request, template_name, {'doc'  : doc,})

@login_required()
def data_document_delete(request, pk, template_name='data_source/datasource_confirm_delete.html'):
    doc = get_object_or_404(DataDocument, pk=pk)
    datagroup_id = doc.data_group_id
    if request.method == 'POST':
        doc.delete()
        return redirect('data_group_detail', pk=datagroup_id)
    return render(request, template_name, {'object': doc})

@login_required
def dg_dd_csv_view(request, pk, template_name='data_group/docs_in_data_group.csv'):
    qs = DataDocument.objects.filter(data_group_id=pk)
    filename = DataGroup.objects.get(pk=pk).name
    return render_to_csv_response(qs, filename=filename, append_datestamp=True)

@login_required()
def habitsandpractices(request, pk,
                      template_name='data_group/habitsandpractices.html'):
    doc = get_object_or_404(DataDocument, pk=pk, )
    script = Script.objects.last() # this needs to be changed bewfore checking in!
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
        # HPFormSet()
        print(hp_formset.is_valid())
        # print(ext_form.cleaned_data['data_document'])
        # print(ext_form.cleaned_data['extraction_script'])
        # print(ext_form.cleaned_data['doc_date'])
        # print(ext_form.non_field_errors())
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
        # render(request, template_name, context)
        # return redirect('habitsandpractices', pk=doc.id)
    return render(request, template_name, context)
