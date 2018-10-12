from django import forms
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from dashboard.forms import HnPFormSet, ChemicalFormSet

from djqscsv import render_to_csv_response

from dashboard.models import *

class DocumentTypeForm(forms.ModelForm):
    class Meta:
        model = DataDocument
        fields = ['document_type']

    def __init__(self, *args, **kwargs):
        super(DocumentTypeForm, self).__init__(*args, **kwargs)
        self.fields['document_type'].label = ''
        self.fields['document_type'].widget.attrs.update({
            'onchange': 'form.submit();'
        })

class ExtractedTextForm(forms.ModelForm):
    class Meta:
        model = ExtractedText
        fields = ['prod_name',
                  'rev_num',
                  'doc_date']


@login_required()
def data_document_detail(request, pk,
                         template_name='data_document/data_document_detail.html'):
    doc = get_object_or_404(DataDocument, pk=pk, )
    extracted_text = ExtractedText.objects.filter(data_document=doc).get()
    extracted_text_form = ExtractedTextForm(instance=extracted_text)
    chemical_formset = ChemicalFormSet(instance=extracted_text, prefix='chemicals')
    habits_and_practices_formset = HnPFormSet(instance=extracted_text, prefix='habits_and_practices')
    document_type_form = DocumentTypeForm(instance=doc)
    if request.method == 'POST' and 'save_extracted_text' in request.POST:
        extracted_text_form = ExtractedTextForm(request.POST, instance=extracted_text)
        if extracted_text_form.is_valid():
            extracted_text_form.save()
    elif request.method == 'POST' and 'save_habits_and_practices' in request.POST:
        habits_and_practices_formset = HnPFormSet(request.POST, instance=extracted_text, prefix='habits_and_practices')
        if habits_and_practices_formset.is_valid():
            habits_and_practices_formset.save()
    elif request.method == 'POST' and 'save_chemicals' in request.POST:
        chemical_formset = ChemicalFormSet(request.POST, instance=extracted_text, prefix='chemicals')
        if chemical_formset.is_valid():
            chemical_formset.save()
    elif request.method == 'POST':
        document_type_form = DocumentTypeForm(request.POST, instance=doc)
        if document_type_form.is_valid():
            document_type = document_type_form.cleaned_data['document_type']
            doc.document_type = document_type
            doc.save()
    habits_and_practices_formset.extra = 0
    document_type_form.fields['document_type'].queryset = \
        document_type_form.fields['document_type'].queryset.filter(group_type_id = doc.data_group.group_type_id)
    if not document_type_form.fields['document_type'].queryset.count():
        document_type_form = False
    context = {'doc': doc,
               'extracted_text': extracted_text,
               'extracted_text_form': extracted_text_form,
               'chemical_formset': chemical_formset,
               'habits_and_practices_formset': habits_and_practices_formset,
               'document_type_form': document_type_form}
    return render(request, template_name, context)

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
