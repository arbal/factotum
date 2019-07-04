from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.http import HttpResponse, HttpResponseRedirect
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
import json

from dashboard.forms import create_detail_formset, QANotesForm, DocumentTypeForm
from dashboard.models import Script, DataGroup, DataDocument,\
    ExtractedCPCat, ExtractedText, ExtractedListPresence,\
    QANotes, DocumentType
from factotum.settings import EXTRA
from django import forms
from django.utils.http import is_safe_url


@login_required()
def qa_extractionscript_index(request, template_name='qa/extraction_script_index.html'):
    datadocument_count = Count('extractedtext__extraction_script')
    qa_complete_extractedtext_count = Count('extractedtext', filter=Q(extractedtext__qa_checked=True))
    extraction_scripts = Script.objects.\
        annotate(datadocument_count=datadocument_count).\
        annotate(qa_complete_extractedtext_count=qa_complete_extractedtext_count).\
        filter(script_type='EX')

    return render(request, template_name, {'extraction_scripts': extraction_scripts})

@login_required()
def qa_chemicalpresence_index(request, template_name='qa/chemical_presence_index.html'):
    datagroups = DataGroup.objects.filter(group_type__code='CP').\
        annotate(datadocument_count=Count('datadocument')).\
        annotate(approved_count=Count('datadocument__extractedtext', 
        filter=Q(datadocument__extractedtext__qa_checked=True)))

    return render(request, template_name, {'datagroups': datagroups})

@login_required()
def qa_chemicalpresence_group(request, pk, template_name='qa/chemical_presence.html'):
    datagroup = DataGroup.objects.get(pk=pk)
    if datagroup.group_type.code != 'CP':
        raise ValidationError('This DataGroup is not of a ChemicalPresence type')
    extractedcpcats = ExtractedCPCat.objects.filter(data_document__data_group=datagroup)
    return render(request, template_name, {'datagroup':datagroup, 'extractedcpcats':extractedcpcats})

def prep_cp_for_qa(extractedcpcat):
    '''
    Given an ExtractedCPCat object, select a sample of its ExtractedListPresence children
    for QA review.
    '''
    from random import shuffle
    QA_RECORDS_PER_DOCUMENT = 30

    if extractedcpcat.rawchem.count() > 0:
        list_presence_count = extractedcpcat.rawchem.count()
    else:
        return
    elps = extractedcpcat.rawchem.select_subclasses()
    non_qa_list_presence_ids = list(elps.filter(extractedlistpresence__qa_flag=False).values_list('pk',flat=True))

    # total number of qa-flagged listpresence objects
    list_presence_qa_count = elps.filter(extractedlistpresence__qa_flag=True).count()

    # if less than 30 records (or all records in set) flagged for QA, make up the difference
    if list_presence_qa_count < QA_RECORDS_PER_DOCUMENT and list_presence_qa_count < list_presence_count:
        random_x = QA_RECORDS_PER_DOCUMENT - list_presence_qa_count
        shuffle(non_qa_list_presence_ids)
        list_presence = ExtractedListPresence.objects.filter(pk__in=non_qa_list_presence_ids[:random_x])
        for lp in list_presence:
            lp.qa_flag = True
            lp.save()
    return


@login_required()
def qa_extraction_script(request, pk,
                         template_name='qa/extraction_script.html'):
    """
    The user reviews the extracted text and checks whether it was properly converted to data
    """
    script = get_object_or_404(Script, pk=pk)
    # If the Script has no related ExtractedText objects, redirect back to the QA index
    if ExtractedText.objects.filter(extraction_script = script).count() == 0 :
        return redirect('/qa/extractionscript/')
    qa_group = script.get_or_create_qa_group()
    texts = ExtractedText.objects.filter(qa_group=qa_group, qa_checked=False)
    return render(request, template_name, {'extractionscript': script,
                                           'extractedtexts': texts,
                                           'qagroup': qa_group})


@login_required()
def qa_extraction_script_summary(request, pk,
                         template_name='qa/extraction_script_summary.html'):
    datadocument_count = Count('extractedtext__extraction_script')
    qa_complete_extractedtext_count = Count('extractedtext', filter=Q(extractedtext__qa_checked=True))
    script = Script.objects.filter(pk=pk).\
        annotate(extractedtext_count=datadocument_count).\
        annotate(qa_complete_extractedtext_count=qa_complete_extractedtext_count). \
        annotate(qa_incomplete_extractedtext_count=datadocument_count - qa_complete_extractedtext_count).first()
    qa_group = script.get_or_create_qa_group()
    qa_notes = QANotes.objects.filter(extracted_text__in = script.extractedtext_set.all())
    return render(request, template_name, {'extractionscript': script, 'qa_group': qa_group, 'qa_notes': qa_notes})


def hide_dsstox_fields(formset):
    # Hide the curated DSSToxLookup fields in the formset if they appear
    for form in formset:
        for dssfield in ['true_cas','true_chemname','SID']:
            if dssfield in form.fields:
                form.fields[dssfield].widget = forms.HiddenInput()


@login_required()
def extracted_text_qa(request, pk,
                      template_name='qa/extracted_text_qa.html', nextid=0):
    """
    Detailed view of an ExtractedText object, where the user can approve the
    record, edit its ExtractedChemical objects, skip to the next ExtractedText
    in the QA group, or exit to the index page.
    This view processes objects of different models with different QA workflows. 
    The qa_focus variable is used to indicate whether an ExtractedText object is
    part of a QA Group, as with Composition records, or if the DataDocument/ExtractedText
    is its own QA Group, as with ExtractedCPCat and ExtractedHHDoc records.  
    """
    extext = get_object_or_404(
	        ExtractedText.objects.select_subclasses(), pk=pk)
    
    doc = DataDocument.objects.get(pk=pk)
    exscript = extext.extraction_script
    group_type_code = extext.data_document.data_group.group_type.code

    if group_type_code in ['CP','HH']:
        qa_focus = 'doc'
        #
        # Document-focused QA process
        #
        # If the object is an ExtractedCPCat record, there will be no Script
        # associated with it and no QA Group
        prep_cp_for_qa(extext)

        stats = ''
        qa_home_page = f'qa/chemicalpresencegroup/%s/' % extext.data_document.data_group.id
    else:
        qa_focus = 'script'
        #
        # Extraction Script-focused QA process
        #
        # when not coming from extraction_script page, the document's script might not have 
        # a QA Group yet. 
        if not extext.qa_group:
            # create the qa group with the optional ExtractedText pk argument
            # so that the ExtractedText gets added to the QA group even if the
            # group uses a random sample
            qa_group = exscript.create_qa_group(pk)
            exscript.qa_begun = True
            exscript.save()
            extext.qa_group = qa_group
            extext.save()
        # get the next unapproved Extracted Text object
        # Its ID will populate the URL for the "Skip" button
        if extext.qa_checked:  # if ExtractedText object's QA process done, use 0
            nextid = 0
        else:
            nextid = extext.next_extracted_text_in_qa_group()
        # derive number of approved records and remaining unapproved in QA Group
        a = extext.qa_group.get_approved_doc_count()
        r = ExtractedText.objects.filter(qa_group=extext.qa_group).count() - a
        stats = '%s document(s) approved, %s documents remaining' % (a, r)

    referer = 'data_document' if 'datadocument' in request.path else 'qa_extraction_script'

    # Create the formset factory for the extracted records
    # The model used for the formset depends on whether the
    # extracted text object matches a data document()
    # The QA view should exclude the weight_fraction_type field.
    ParentForm, ChildForm = create_detail_formset(
        doc, EXTRA, can_delete=True, 
        exclude=['weight_fraction_type', 'true_cas', 'true_chemname', 'sid'])
    # extext = extext.pull_out_cp()
    ext_form = ParentForm(instance=extext)
    detail_formset = ChildForm(instance=extext)
    
    # If the document is CPCat or HHE type, the display should only show the
    # child records where qa_flag = True
    if qa_focus == 'doc' and hasattr(detail_formset.get_queryset().model, 'qa_flag'):
        qs = detail_formset.get_queryset().filter(qa_flag=True)
        detail_formset._queryset = qs
    
    # This code is being repeated in the GET and POST blocks
    # 
    # Hide all the DSSToxLookup fields 
    hide_dsstox_fields(detail_formset)

    # Add CSS selector classes to each form
    for form in detail_formset:
        for field in form.fields:
            form.fields[field].widget.attrs.update(
                {'class': f'detail-control form-control %s' % doc.data_group.type}
            )

    note, created = QANotes.objects.get_or_create(extracted_text=extext)
    notesform = QANotesForm(instance=note)

    # Allow the user to edit the data document type
    document_type_form = DocumentTypeForm(request.POST or None, instance=doc)
    qs = DocumentType.objects.compatible(doc)
    document_type_form.fields['document_type'].queryset = qs
    # the form class overrides the label, so over-override it
    document_type_form.fields['document_type'].label = 'Data document type:'

    context = {
        'extracted_text': extext,
        'doc': doc,
        'script': exscript,
        'stats': stats,
        'nextid': nextid,
        'detail_formset': detail_formset,
        'notesform': notesform,
        'ext_form': ext_form,
        'referer': referer,
        'document_type_form': document_type_form
    }

    if request.method == 'POST' and 'save' in request.POST:
        # The save action only applies to the child records and QA properties,
        # no need to save the ExtractedText form
        ParentForm, ChildForm = create_detail_formset(
            doc, EXTRA, can_delete=True, exclude=['weight_fraction_type'])
        # extext = extext.pull_out_cp()
        detail_formset = ChildForm(request.POST, instance=extext)

        if detail_formset.has_changed():
            if detail_formset.is_valid() :
                detail_formset.save()
                extext.qa_edited = True
                extext.save()
                # rebuild the formset after saving it
                detail_formset = ChildForm(instance=extext)
            else:
                pass
                # print(detail_formset.errors)
                # TODO: iterate through this dict of errors and map each error to
                # the corresponding form in the template for rendering

            context['detail_formset'] = detail_formset
            context['ext_form'] = ext_form

        # This code is being repeated in the GET and POST blocks
        # 
        # Hide all the DSSToxLookup fields 
        hide_dsstox_fields(detail_formset)

        # Add CSS selector classes to each form
        for form in detail_formset:
            for field in form.fields:
                form.fields[field].widget.attrs.update(
                    {'class': f'detail-control form-control %s' % doc.data_group.type}
                )

    return render(request, template_name, context)


@login_required()
def save_qa_notes(request, pk):
    '''
    This is an endpoint that serves the AJAX call
    '''
    if request.method == 'POST':
        qa_note_text = request.POST.get('qa_note_text')

        response_data = {}
        
        et = ExtractedText.objects.get(pk=pk)

        qa, created = QANotes.objects.get_or_create(extracted_text=et)
        qa.qa_notes = qa_note_text
        qa.save()

        response_data['result'] = 'QA Note edits successfully saved'
        response_data['qa_note_text'] = qa.qa_notes

        return HttpResponse(
            json.dumps(response_data),
            content_type="application/json"
        )
    else:
        return HttpResponse(
            json.dumps({"not a POST request": "this will not happen"}),
            content_type="application/json"
        )

@login_required()
def approve_extracted_text(request, pk):
    '''
    This is an endpoint that processes the ExtractedText approval
    '''
    extext = get_object_or_404(
	        ExtractedText.objects.select_subclasses(), pk=pk)
    nextpk = extext.next_extracted_text_in_qa_group()
    
    
    if request.method == 'POST':
        if extext.is_approvable():
            extext.qa_approved_date = timezone.now()
            extext.qa_approved_by = request.user
            extext.qa_checked = True
            extext.save()
            # The ExtractedText record is now approved.
            # Redirect to the appropriate page.

            referer = request.POST.get('referer', '') 
            if referer == 'data_document':
                # The user got to the QA page from a data document detail page,
                # so return there
                redirect_to = reverse(referer, kwargs={'pk': pk})
            elif not nextpk == 0:
                redirect_to = reverse('extracted_text_qa', args=[(nextpk)])
            elif nextpk == 0:
                # return to the top of the most local QA stack.
                # that may be the list of ExtractionScripts or 
                # the list of Chemical Presence Data Groups
                redirect_to = extext.get_qa_index_path()

            messages.success(request, "The extracted text has been approved!")
            if is_safe_url(url=redirect_to, allowed_hosts=request.get_host()):
                return HttpResponseRedirect(redirect_to)
            else:
                return HttpResponseRedirect(
                    reverse('extracted_text_qa', args=[(pk)]))
        else:
            # The ExtractedText record cannot be approved.
            # Return to the QA page and display an error.
            messages.error(request, "The extracted text \
                could not be approved. Make sure that if the records have been edited,\
                the QA Notes have been populated.")
            return HttpResponseRedirect(
                    reverse('extracted_text_qa', args=[(pk)]))

        
        

