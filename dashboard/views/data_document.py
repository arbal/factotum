from django import forms
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from dashboard.forms import (ExtractedTextForm, ExtractedCPCatForm,
                                DocumentTypeForm,
                                create_detail_formset)

from djqscsv import render_to_csv_response

from factotum.settings import EXTRA # if this goes to 0, tests will fail because of what num form we search for
from dashboard.models import *

@login_required()
def data_document_detail(request, pk,
                         template_name='data_document/data_document_detail.html'):
    doc = get_object_or_404(DataDocument, pk=pk, )
    ParentForm, ChildForm = create_detail_formset(doc.data_group.type, extra=0, can_delete=False)

    document_type_form = DocumentTypeForm(request.POST or None, instance=doc)
    qs = DocumentType.objects.filter(group_type=doc.data_group.group_type)
    document_type_form.fields['document_type'].queryset = qs

    context = {'doc': doc,
            'document_type_form': document_type_form}

    try:
        extracted_text = ExtractedText.objects.get(data_document=doc)

    except ExtractedText.DoesNotExist:
        #print('No ExtractedText object found for DataDocument: %s' % doc )
        extracted_text = None

    else:
        #print('ExtractedText object found: %s' % extracted_text )
        extracted_text = extracted_text.pull_out_cp() #get CP if exists
        extracted_text_form = ParentForm(instance=extracted_text)
        child_formset = ChildForm(instance=extracted_text)


        for form in child_formset.forms:
            for field in form.fields:
                form.fields[field].widget.attrs['disabled'] = True

        context.update(
            {'extracted_text': extracted_text,
            'detail_formset': child_formset}
            )
                
        colors = ['#d6d6a6','#dfcaa9','#d8e5bf'] * 47
        color = (hex for hex in colors)
        for form in child_formset.forms:
            form.color = next(color)
    return render(request, template_name, context)

@login_required()
def save_doc_form(request, pk):
    doc = get_object_or_404(DataDocument, pk=pk)
    document_type_form = DocumentTypeForm(request.POST, instance=doc)
    if document_type_form.is_valid() and document_type_form.has_changed():
        document_type_form.save()
    return redirect('data_document', pk=pk)

@login_required()
def save_ext_form(request, pk):
    doc = get_object_or_404(DataDocument, pk=pk)
    ExtractedTextForm, _ = create_detail_formset(doc.data_group.type)
    extracted_text = doc.extractedtext.pull_out_cp()
    ext_text_form = ExtractedTextForm(request.POST, instance=extracted_text)
    if ext_text_form.is_valid() and ext_text_form.has_changed():
        ext_text_form.save()
    return redirect('data_document', pk=pk)

@login_required()
def data_document_delete(request, pk, template_name='data_source/datasource_confirm_delete.html'):
    doc = get_object_or_404(DataDocument, pk=pk)
    datagroup_id = doc.data_group_id
    if request.method == 'POST':
        doc.delete()
        return redirect('data_group_detail', pk=datagroup_id)
    return render(request, template_name, {'object': doc})

@login_required
def dg_dd_csv_view(request, pk):
    qs = DataDocument.objects.filter(data_group_id=pk)
    filename = DataGroup.objects.get(pk=pk).name
    return render_to_csv_response(qs, filename=filename, append_datestamp=True)
