import os
import math
from random import shuffle
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.forms import (ModelForm, Form, BaseInlineFormSet,
                            inlineformset_factory, TextInput, CharField,
                            Textarea, HiddenInput, ValidationError)

from django.urls import reverse
from django.utils import timezone
from django.core.files import File
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.decorators import login_required

from dashboard.models import (DataGroup, DataDocument, DataSource, QANotes,
                              ExtractedText, Script, QAGroup, ExtractedChemical)


class ExtractionScriptForm(ModelForm):
    required_css_class = 'required'  # adds to label tag

    class Meta:
        model = Script
        fields = ['title', 'url', 'qa_begun']
        labels = {
            'qa_begun': _('QA has begun'),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(ExtractionScriptForm, self).__init__(*args, **kwargs)

class ExtractedTextForm(ModelForm):

    class Meta:
        model = ExtractedText
        fields = ['prod_name', 'doc_date', 'rev_num']

class QANotesForm(ModelForm):

    class Meta:
        model = QANotes
        fields = ['qa_notes']
        widgets = {
            'qa_notes' : Textarea,
        }
        labels = {
            'qa_notes': _('QA Notes (required if approving edited records)'),
        }




class BaseExtractedChemicalFormSet(BaseInlineFormSet):
    """
    Base class for the form in which users edit the chemical composition data
    """
    required_css_class = 'required'  # adds to label tag

    class Meta:
        model = ExtractedChemical
        # fields = ['raw_cas', 'raw_chem_name', 'raw_min_comp',
        #           'raw_max_comp', 'unit_type', 'report_funcuse', 'extracted_text']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(BaseExtractedChemicalFormSet, self).__init__(*args, **kwargs)
        for form in self.forms:
            for field in form.fields:
                form.fields[field].widget.attrs.update(
                                        {'class': 'chem-control form-control'})



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


class ExtractedTextQAForm(ModelForm):
    required_css_class = 'required'  # adds to label tag

    class Meta:
        model = ExtractedText
        fields = ['prod_name', 'data_document', 'qa_checked']



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
    datadoc = DataDocument.objects.get(pk=pk)
    exscript = extext.extraction_script
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
    # Create the formset factory for the extracted chemical records
    ChemFormSet = inlineformset_factory(parent_model=ExtractedText,
                                        model=ExtractedChemical,
                                        formset=BaseExtractedChemicalFormSet,
                                        fields=['extracted_text','raw_cas',
                                                'raw_chem_name', 'raw_min_comp',
                                                'raw_max_comp', 'unit_type',
                                                'report_funcuse',
                                                'ingredient_rank',
                                                'raw_central_comp'],
                                                extra=1)
    ext_form =  ExtractedTextForm(instance=extext)
    note, created = QANotes.objects.get_or_create(extracted_text=extext)
    notesform =  QANotesForm(instance=note)
    chem_formset = ChemFormSet(instance=extext, prefix='chemicals')
    context = {
        'extracted_text': extext,
        'doc': datadoc,
        'script': exscript,
        'stats': stats,
        'nextid': nextid,
        'chem_formset': chem_formset,
        'notesform': notesform,
        'ext_form': ext_form
        }

    if request.method == 'POST' and 'save' in request.POST:
        print('---saving')
        chem_formset = ChemFormSet(request.POST, instance=extext,
                                                        prefix='chemicals')
        ext_form =  ExtractedTextForm(request.POST, instance=extext)
        notesform = QANotesForm(request.POST, instance=note)
        if chem_formset.has_changed() or ext_form.has_changed():
            print(str(extext.qa_edited))
            if chem_formset.is_valid() and ext_form.is_valid():
                chem_formset.save()
                ext_form.save()
                extext.qa_edited = True
                extext.save()
        context['chem_formset'] = chem_formset
        context['ext_form'] = ext_form
        # context['notesform'] = notesform
        context.update({'notesform' : notesform}) # calls the clean method? y?

    # APPROVAL
    elif request.method == 'POST' and 'approve' in request.POST:
        print('--approve')
        notesform =  QANotesForm(request.POST, instance=note)
        context['notesform'] = notesform
        nextpk = extext.next_extracted_text_in_qa_group()
        if notesform.is_valid():
            extext.qa_approved_date = timezone.now()
            extext.qa_approved_by =  request.user
            extext.qa_checked =  True
            extext.save()
            notesform.save()
            if not nextpk == 0:
                return HttpResponseRedirect(
                            reverse('extracted_text_qa', args=[(nextpk)]))
            if nextpk == 0:
                return HttpResponseRedirect(
                            reverse('qa'))

    return render(request, template_name, context)
