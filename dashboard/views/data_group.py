import os
import csv
import zipfile
from datetime import datetime

from django.conf import settings
from django.forms import ModelForm, Form
from django import forms
from django.core.files import File
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from bootstrap_datepicker.widgets import DatePicker

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from djqscsv import *

from dashboard.models import (DataGroup, DataDocument, DocumentType, Script, ExtractedText, ExtractedChemical, WeightFractionType)


class DataGroupForm(ModelForm):
    required_css_class = 'required' # adds to label tag
    # source_type = forms.ModelChoiceField(label='Document Default Source Type',
                                         # queryset=SourceType.objects.all())
    class Meta:
        model = DataGroup
        fields = ['name', 'description', 'group_type', 'downloaded_by', 'downloaded_at', 'download_script', 'data_source', 'csv']
        widgets = {
            'downloaded_at': DatePicker(options={
                "format": "yyyy-mm-dd",
                "autoclose": True
            })
        }
        labels = {'csv': _('Register Records CSV File'), }

    def __init__(self, *args, **kwargs):
        qs = Script.objects.filter(script_type='DL')
        self.user = kwargs.pop('user', None)
        super(DataGroupForm, self).__init__(*args, **kwargs)
        self.fields['csv'].widget.attrs.update({'accept':'.csv'})
        self.fields['download_script'].queryset = qs

class ExtractionScriptForm(Form):
    required_css_class = 'required' # adds to label tag
    script_selection = forms.ModelChoiceField(queryset=Script.objects.filter(script_type='EX')
                                              , label="Extraction Script")
    weight_fraction_type = forms.ModelChoiceField(queryset=WeightFractionType.objects.all()
                                                  , label="Weight Fraction Type"
                                                  , initial="1")
    extract_file = forms.FileField(label="Extracted Text CSV File")

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(ExtractionScriptForm, self).__init__(*args, **kwargs)
        self.fields['weight_fraction_type'].widget.attrs.update({'style':'height:2.75rem; !important'})
        self.fields['script_selection'].widget.attrs.update({'style':'height:2.75rem; !important'})
        self.fields['extract_file'].widget.attrs.update({'accept':'.csv'})
        self.collapsed = True


@login_required()
def data_group_list(request, template_name='data_group/datagroup_list.html'):
    datagroup = DataGroup.objects.all()
    data = {}
    data['object_list'] = datagroup
    return render(request, template_name, data)


def loadExtracted (row, dd, sc):
    if ExtractedText.objects.filter(data_document=dd):
        t = ExtractedText.objects.get(data_document=dd)
        return t
    else:
        t = ExtractedText(	data_document     = dd,
                              record_type       = row['record_type'],
                              prod_name         = row['prod_name'],
                              doc_date          = row['doc_date'],
                              rev_num           = row['rev_num'],
                              extraction_script = sc)
    return t


@login_required()
def data_group_detail(request, pk,
                      template_name='data_group/datagroup_detail.html'):
    datagroup = get_object_or_404(DataGroup, pk=pk, )
    docs = DataDocument.objects.filter(data_group_id=pk).order_by('title')
    npage = 50 # TODO: make this dynamic someday in its own ticket
    page = request.GET.get('page')
    page = 1 if page is None else page
    scripts = Script.objects.filter(script_type='EX')
    store = settings.MEDIA_URL + datagroup.name.replace(' ','_')
    extract_fieldnames = ['data_document_pk','data_document_filename',
                          'record_type','prod_name','doc_date','rev_num',
                          'raw_cas', 'raw_chem_name','raw_min_comp',
                          'raw_max_comp', 'unit_type', 'report_funcuse',
                          'ingredient_rank', 'raw_central_comp']
    extract_form = ExtractionScriptForm(request.POST or None,request.FILES or None )

    err = False
    ext_err = {}

    if request.method == 'POST' and 'upload' in request.POST:
        files = request.FILES.getlist('multifiles')
        # match filename to pdf name
        proc_files = [f for d in docs for f in files if f.name == d.filename]
        if not proc_files:
            err = True
        zf = zipfile.ZipFile(datagroup.zip_file, 'a', zipfile.ZIP_DEFLATED)
        while proc_files:
            pdf = proc_files.pop(0)
            # set the Matched value of each registered record to True
            doc = DataDocument.objects.get(filename=pdf.name, data_group=datagroup.pk)
            if doc.matched:  # skip if already matched
                continue
            doc.matched = True
            doc.save()
            fs = FileSystemStorage(store + '/pdf')
            fs.save(pdf.name, pdf)
            zf.write(store + '/pdf/' + pdf.name, pdf.name)
        zf.close()
    if request.method == 'POST' and 'extract_button' in request.POST:
        extract_form.collapsed = False
        if extract_form.is_valid():
            csv_file = request.FILES.getlist('extract_file')[0]
            weight_fraction_type = request.POST['weight_fraction_type']
            script = Script.objects.get(pk=request.POST['script_selection'])
            info = [x.decode('ascii','ignore') for x in csv_file.readlines()]
            table = csv.DictReader(info)
            throw = 0
            if not table.fieldnames == extract_fieldnames:
                for i, col in enumerate(table.fieldnames):
                    if not col in extract_fieldnames:
                        good = extract_fieldnames[i]
                        ext_err['every'] = {col:['needs to be renamed to "%s"' % good]}
                for col in extract_fieldnames:
                    if not col in table.fieldnames:
                        ext_err['every'] = {col:['needs to be a column in the uploaded file']}
                return render(request, template_name,
                              {   'datagroup'         : datagroup,
                                  'documents'         : docs,
                                  'include_upload'    : False,
                                  'err'               : err,
                                  'include_extract'   : True,
                                  'scripts'           : scripts,
                                  'extract_fieldnames': extract_fieldnames,
                                  'ext_err'           : ext_err,
                                  'extract_form'      : extract_form})
            record = 1
            for row in csv.DictReader(info):
                doc_pk = (row['data_document_pk'])
                doc = docs.get(pk=doc_pk)
                # load and validate ALL ExtractedText records
                # see if it exists if true continue else validate, don't save
                text = loadExtracted(row, doc, script)
                try:
                    text.full_clean()
                except ValidationError as e:
                    throw = 1
                    ext_err[record] = e.message_dict
                    # send back to user if not all text records pass validation
                record += 1
            if throw:
                return render(request, template_name,
                              {   'datagroup'         : datagroup,
                                  'documents'         : docs,
                                  'include_upload'        : False,
                                  'err'               : err,
                                  'include_extract'   : True,
                                  'scripts'           : scripts,
                                  'extract_fieldnames': extract_fieldnames,
                                  'ext_err'           : ext_err,
                                  'extract_form'      : extract_form})
            good_chems = []
            record = 1
            for row in csv.DictReader(info):
                doc_pk = (row['data_document_pk'])
                doc = docs.get(pk=doc_pk)
                text = loadExtracted(row, doc, script)
                if not ExtractedText.objects.filter(data_document=doc):
                    text.save()
                # see if chem already assigned to text ultimately DD
                qs = ExtractedChemical.objects.filter(  # empty queryset if no
                    chem_name=row['chem_name']).values_list(
                    'extracted_text_id')
                #check qs if returned
                check = any([t_id[0] == text.pk for t_id in qs])
                if check:
                    continue
                if not check:
                    chem = ExtractedChemical(extracted_text = text,
                                cas                 = row['raw_cas'],
                                chem_name           = row['raw_chem_name'],
                                raw_min_comp        = row['raw_min_comp'],
                                raw_max_comp        = row['raw_max_comp'],
                                unit_type           = row['unit_type'],
                                report_funcuse      = row['report_funcuse'],
                                weight_fraction_type= weight_fraction_type,
                                ingredient_rank     = row['ingredient_rank'],
                                raw_central_comp    = row['raw_central_comp'],
                                             )
                    try:
                        chem.full_clean()
                        good_chems.append([doc,chem])
                    except ValidationError as e:
                        ext_err[record] = e.message_dict
                record += 1

            if not ext_err:  # no saving until all errors are removed
                for doc, chem in good_chems:
                    doc.extracted = True
                    doc.save()
                    chem.save()
                fs = FileSystemStorage(store)
                fs.save(str(datagroup)+'_extracted.csv', csv_file)

    paginator = Paginator(docs, npage) # Show 25 data documents per page
    docs_page = paginator.page(page)

    include_upload = not all([d.matched for d in docs])
    include_extract = all([d.matched for d in docs]) \
                      and not all([d.extracted for d in docs])

    return render(request, template_name,{
        'datagroup'         : datagroup,
        'documents'         : docs_page,
        'all_documents'     : docs,
        'include_upload'    : include_upload,
        'err'               : err,
        'include_extract'   : include_extract,
        'scripts'           : scripts,
        'extract_fieldnames': extract_fieldnames,
        'ext_err'           : ext_err,
        'extract_form'      : extract_form})


@login_required()
def data_group_create(request, template_name='data_group/datagroup_form.html'):
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
        # source_type = SourceType.objects.get(pk=form.data['source_type'])
        if form.is_valid():
            datagroup = form.save()
            info = [x.decode('ascii',
                             'ignore') for x in datagroup.csv.readlines()]
            table = csv.DictReader(info)
            if not table.fieldnames == ['filename','title','document_type','product','url']:
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
                    if DocumentType.objects.filter(pk=line['document_type']).exists():
                        doc_type = DocumentType.objects.get(pk=line['document_type'])
                    else:
                        errors.append(count)
                doc=DataDocument(filename=line['filename'],
                                 title=line['title'],
                                 document_type=doc_type,
                                 product_category=line['product'],
                                 url=line['url'],
                                 # source_type=source_type,
                                 data_group=datagroup)
                print(doc)
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


@login_required
def dg_dd_csv_view(request, pk, template_name='data_group/docs_in_data_group.csv'):
    qs = DataDocument.objects.filter(data_group_id=pk)
    filename = DataGroup.objects.get(pk=pk).name
    return render_to_csv_response(qs, filename=filename, append_datestamp=True)
