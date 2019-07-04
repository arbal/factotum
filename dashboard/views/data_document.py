from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.contrib import messages

from dashboard.forms import ExtractedListPresenceTagForm, create_detail_formset, DataDocumentForm, DocumentTypeForm
from dashboard.models import DataDocument, ExtractedListPresence, ExtractedText, Script, ExtractedListPresenceToTag



@login_required()
def data_document_detail(request, pk):
    template_name = 'data_document/data_document_detail.html'
    doc = get_object_or_404(DataDocument, pk=pk, )
    ParentForm, ChildFormSet = create_detail_formset(doc,
                                extra=(1 if doc.detail_page_editable else 0))
    context = {'doc': doc}
    if doc.is_extracted:
        extracted_inst = ExtractedText.objects.get_subclass(pk=doc.pk)
        objs = {'edit_text_form': ParentForm(instance=extracted_inst),
                'extracted_text': extracted_inst,
                'detail_formset': ChildFormSet(instance=extracted_inst)}
        context.update(objs)
        if doc.data_group.group_type.code == 'CP':
            lp = ExtractedListPresence.objects.filter(
                                            extracted_text=doc.extractedtext)
            if lp.exists():
                list_presence = lp.first()
                tag_form = ExtractedListPresenceTagForm(instance=list_presence)
                context.update({'list_presence_tag_form': tag_form})
    else:
        context['edit_text_form'] = ParentForm()
    if request.method == 'POST':
        card = request.POST.get('CARD', '')
        child_formset = ChildFormSet(request.POST, instance=doc.extractedtext)
        if child_formset.is_valid():
            child_formset.save()
            if not card: # grab pk of new chem if being added
                form = child_formset[-1]
                card = f'#chem-{form.instance.pk}'
            url = reverse('data_document', args=[doc.pk])
            url += card
            return redirect(url)
        context.update({'detail_formset': child_formset})
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
    tag_form = None
    for extracted_list_presence in extracted_text.rawchem.select_subclasses('extractedlistpresence'):
        tag_form = ExtractedListPresenceTagForm(request.POST or None, instance=extracted_list_presence)
        if tag_form.is_valid():
            tag_form.save()
        else:
            messages.error(request,tag_form.errors['tags'])
            break
    if not len(tag_form.errors):
        messages.success(request,
            "The following keywords are now associated with these list presence objects: %s" % tag_form['tags'].data)
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
    try:
        extracted_text = model.objects.get_subclass(data_document_id=pk)
    except ExtractedText.DoesNotExist:
        extracted_text = model(data_document_id=pk, extraction_script=script)
    form = ParentForm(request.POST, instance=extracted_text)
    if form.is_valid():
        form.save()
        doc.save()
        return redirect('data_document', pk=doc.pk)
    else:
        extracted_text.delete()
        return HttpResponse("Houston, we have a problem.")

@login_required
def list_presence_tag_curation(request, template_name='data_document/list_presence_tag.html'):
    documents = DataDocument.objects.filter(data_group__group_type__code='CP').\
        exclude(extractedtext__rawchem__in=ExtractedListPresenceToTag.objects.values('content_object_id'))
    return render(request, template_name, {'documents': documents})


