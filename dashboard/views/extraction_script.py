import os
import math
from random import shuffle
from urllib import parse

from django.conf import settings
from django.urls import reverse, resolve
from django.http import HttpResponseRedirect
from django.forms import inlineformset_factory
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.core.files import File
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.decorators import login_required

from factotum.settings import EXTRA
from dashboard.models import *
from dashboard.utils import get_extracted_models
from dashboard.forms import (BaseExtractedDetailFormSet, ExtractedTextForm,
                            create_detail_formset,   QANotesForm)


from factotum.settings import EXTRA # if this goes to 0, tests will fail because of what num form we search for


@login_required()
def extraction_script_list(request, template_name='qa/extraction_script_list.html'):
    """
    List view of extraction scripts
    """
    # TODO: the user is supposed to be able to click the filter button at the top of the table
    # and toggle between seeing all scripts and seeing only the ones with incomplete QA
    extractionscript = Script.objects.filter(script_type='EX')
    data = {}
    data['object_list'] = extractionscript
    return render(request, template_name, data)


@login_required()
def extraction_script_qa(request, pk,
                         template_name='qa/extraction_script.html'):
    """
    The user reviews the extracted text and checks whether it was properly converted to data
    """
    es = get_object_or_404(Script, pk=pk)
    if es.qa_begun:
        # has qa begun and not complete? if both T, return group to be finished
        if QAGroup.objects.filter(extraction_script=es,
                                  qa_complete=False).exists():
            # return docs that are in extracted texts QA group
            group = QAGroup.objects.get(extraction_script=es,
                                        qa_complete=False)
            texts = ExtractedText.objects.filter(qa_group=group,
                                                 qa_checked=False)
            return render(request, template_name, {'extractionscript': es,
                                                   'extractedtexts': texts,
                                                   'qagroup': group})
    # pks of text and docs are the same!
    doc_text_ids = list(ExtractedText.objects.filter(extraction_script=es,
                                                     qa_checked=False
                                                     ).values_list('pk',
                                                                   flat=True))
    qa_group = QAGroup.objects.create(extraction_script=es)
    if len(doc_text_ids) < 100:
        texts = ExtractedText.objects.filter(pk__in=doc_text_ids)
    else:
        random_20 = math.ceil(len(doc_text_ids)/5)
        shuffle(doc_text_ids)  # this is used to make random selection of texts
        texts = ExtractedText.objects.filter(pk__in=doc_text_ids[:random_20])
    for text in texts:
        text.qa_group = qa_group
        text.save()
    es.qa_begun = True
    es.save()
    return render(request, template_name, {'extractionscript': es,
                                           'extractedtexts': texts,
                                           'qagroup': qa_group})

@login_required()
def extraction_script_detail(request, pk,
                             template_name='extraction_script/extraction_script_detail.html'):
    extractionscript = get_object_or_404(Script, pk=pk)
    data = {}
    data['object_list'] = extractionscript
    return render(request, template_name, data)


@login_required()
def extracted_text_qa(request, pk,
                            template_name='qa/extracted_text_qa.html', nextid=0):
    """
    Detailed view of an ExtractedText object, where the user can approve the
    record, edit its ExtractedChemical objects, skip to the next ExtractedText
    in the QA group, or exit to the index page
    """
    extext = get_object_or_404(ExtractedText, pk=pk)
    # The related DataDocument has the same pk as the ExtractedText object
    doc = DataDocument.objects.get(pk=pk)
    exscript = extext.extraction_script
    # when not coming from extraction_script page, we don't necessarily have a qa_group created
    if not extext.qa_group:
        extext.qa_group = QAGroup.objects.create(extraction_script=exscript)
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
    referer = 'data_document' if 'datadocument' in request.path else 'extraction_script_qa'

    # Create the formset factory for the extracted records
    # The model used for the formset depends on whether the
    # extracted text object matches a data document()
    
    ParentForm, ChildForm = create_detail_formset(doc.data_group.type, EXTRA)
    extext = extext.pull_out_cp() #get CP if exists
    ext_form = ParentForm(instance=extext)
    detail_formset = ChildForm(instance=extext)
    # Add CSS selector classes to each form
    for form in detail_formset:
        for field in form.fields:
            form.fields[field].widget.attrs.update(
                {'class': f'detail-control form-control %s' % doc.data_group.type}
                )

    note, created = QANotes.objects.get_or_create(extracted_text=extext)
    notesform =  QANotesForm(instance=note)

    context = {
        'extracted_text': extext,
        'doc': doc,
        'script': exscript,
        'stats': stats,
        'nextid': nextid,
        'detail_formset': detail_formset,
        'notesform': notesform,
        'ext_form': ext_form,
        'referer': referer
        }

    if request.method == 'POST' and 'save' in request.POST:
        #print(request.__dict__)
       
        ParentForm, ChildForm = create_detail_formset(doc.data_group.type, EXTRA)
        extext = extext.pull_out_cp() #get CP if exists
        ext_form = ParentForm(request.POST, instance=extext)
        detail_formset = ChildForm(request.POST, instance=extext)

        notesform = QANotesForm(request.POST, instance=note)
        if detail_formset.has_changed() or ext_form.has_changed():
            if detail_formset.is_valid() and ext_form.is_valid():
                detail_formset.save()
                ext_form.save()
                extext.qa_edited = True
                extext.save()
        # rebuild the formset after saving it
        detail_formset = ChildForm( instance=extext)
        context['detail_formset'] = detail_formset
        context['ext_form'] = ext_form
        context.update({'notesform' : notesform}) # calls the clean method? y?
        # Add CSS selector classes to each form
        for form in detail_formset:
            for field in form.fields:
                form.fields[field].widget.attrs.update(
                    {'class': f'detail-control form-control %s' % doc.data_group.type}
                    )

    elif request.method == 'POST' and 'approve' in request.POST: # APPROVAL
        notesform =  QANotesForm(request.POST, instance=note)
        context['notesform'] = notesform
        nextpk = extext.next_extracted_text_in_qa_group()
        if notesform.is_valid():
            extext.qa_approved_date = timezone.now()
            extext.qa_approved_by =  request.user
            extext.qa_checked =  True
            extext.save()
            notesform.save()
            if referer == 'data_document':
                return HttpResponseRedirect(
                    reverse(referer, kwargs={'pk': pk}))
            elif not nextpk == 0:
                return HttpResponseRedirect(
                            reverse('extracted_text_qa', args=[(nextpk)]))
            elif nextpk == 0:
                return HttpResponseRedirect(
                            reverse('qa'))
    return render(request, template_name, context)
