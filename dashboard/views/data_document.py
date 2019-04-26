from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from djqscsv import render_to_csv_response

from dashboard.forms import *
from dashboard.forms import ExtractedListPresenceTagForm
# if this goes to 0, tests will fail because of what num form we search for
from factotum.settings import EXTRA
from dashboard.models import *


@login_required()
def data_document_detail(request, pk):
    template_name = 'data_document/data_document_detail.html'
    doc = get_object_or_404(DataDocument, pk=pk, )
    code = doc.data_group.group_type.code
    edit = 1 if doc.detail_page_editable else 0
    # edit adds an extra record to the formset, but is also a switch in the
    # template and to add the delete input, this will only work if we add one at
    # a time...
    ParentForm, ChildFormSet = create_detail_formset(
        doc, extra=edit, can_delete=bool(edit))
    document_type_form = DocumentTypeForm(request.POST or None, instance=doc)
    qs = DocumentType.objects.filter(group_type=doc.data_group.group_type)
    document_type_form.fields['document_type'].queryset = qs
    context = {'doc': doc,
               'edit': edit,
               'document_type_form': document_type_form}
    if code == 'CP':
        # although keywords display as if at the datadocument level, they are
        # attached to each list_presence record. To display, we're getting the
        # tags associated with the first list_presence record, but on saving
        # (in save_list_presence_tag_form()) we loop over the whole set
        try:
            list_presence = doc.extractedtext.rawchem.select_subclasses('extractedlistpresence').first()
            list_presence_tag_form = ExtractedListPresenceTagForm(instance=list_presence)
            context.update({'list_presence_tag_form': list_presence_tag_form})
        except ObjectDoesNotExist:
            pass
    if doc.is_extracted:
        extracted_text = ExtractedText.objects.get_subclass(pk=doc.pk)
        child_formset = ChildFormSet(instance=extracted_text)
        if not edit:
            for form in child_formset.forms:
                for field in form.fields:
                    form.fields[field].widget.attrs['disabled'] = True
        context.update(
            {'edit_text_form': ParentForm(instance=extracted_text),
             'extracted_text': extracted_text,
             'detail_formset': child_formset}
        )

    else:
        context['edit_text_form'] = ParentForm()
    return render(request, template_name, context)


@login_required()
def save_doc_form(request, pk):
    '''Writes changes to the data document form 
    
    The request object should have a 'referer' key to redirect the 
    browser to the appropriate place after saving the edits

    Invoked by changing the document type in the data document detail view or the
    extracted text QA page template
    '''

    referer = request.POST.get('referer', 'data_document')
    doc = get_object_or_404(DataDocument, pk=pk)
    document_type_form = DocumentTypeForm(request.POST, instance=doc)
    if document_type_form.is_valid() and document_type_form.has_changed():
        document_type_form.save()
    return redirect(referer, pk=pk)


@login_required()
def data_document_note(request, pk):
    doc = get_object_or_404(DataDocument, pk=pk)
    doc_note = request.POST['dd_note']
    doc.note = doc_note
    doc.save()
    return redirect('data_document', pk=pk)


@login_required()
def save_ext_form(request, pk):
    referer = request.POST.get('referer', 'data_document')
    doc = get_object_or_404(DataDocument, pk=pk)
    ExtractedTextForm, _ = create_detail_formset(doc)
    extracted_text = ExtractedText.objects.get_subclass(pk=pk)
    ext_text_form = ExtractedTextForm(request.POST, instance=extracted_text)
    if ext_text_form.is_valid() and ext_text_form.has_changed():
        ext_text_form.save()
    return redirect(referer, pk=pk)

@login_required()
def save_list_presence_tag_form(request, pk):
    referer = request.POST.get('referer', 'data_document')
    extracted_text = get_object_or_404(ExtractedText, pk=pk)
    for extracted_list_presence in extracted_text.rawchem.select_subclasses('extractedlistpresence'):
        tag_form = ExtractedListPresenceTagForm(request.POST or None, instance=extracted_list_presence)
        if tag_form.is_valid():
            tag_form.save()
    return redirect(referer, pk=pk)

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

@login_required
def data_document_edit(request, pk, template_name=('data_document/'
                                                    'data_document_form.html')):
    datadocument = get_object_or_404(DataDocument, pk=pk)
    form = DataDocumentForm(request.POST or None, instance=datadocument)
    if form.is_valid():
        if form.has_changed():
            form.save()
        return redirect('data_document', pk=pk)
    form.referer = request.META.get('HTTP_REFERER', None)
    return render(request, template_name, {'form': form})


@login_required
def extracted_text_edit(request, pk):
    doc = get_object_or_404(DataDocument, pk=pk)
    ParentForm, _ = create_detail_formset(doc, extra=0, can_delete=False)
    model = ParentForm.Meta.model
    script = Script.objects.get(title__icontains='Manual (dummy)', script_type='EX')
    exttext, _ = model.objects.get_or_create(extraction_script=script,
                                             data_document_id=pk)
    form = ParentForm(request.POST, instance=exttext)
    if form.is_valid():
        form.save()
        doc.extracted = True
        doc.save()
        return redirect('data_document', pk=doc.pk)
    else:
        extext.delete()
        return HttpResponse("Houston, we have a problem.")


@login_required
def extracted_child_edit(request, pk):
    doc = get_object_or_404(DataDocument, pk=pk)
    _, ChildFormSet = create_detail_formset(doc, extra=1, can_delete=True)
    formset = ChildFormSet(request.POST, instance=doc.extractedtext)
    if formset.is_valid():
        formset.save()
    return redirect('data_document', pk=doc.pk)
