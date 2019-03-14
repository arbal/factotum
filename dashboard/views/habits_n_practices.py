from dal import autocomplete

from django.shortcuts import (render, redirect, get_object_or_404,
                                                HttpResponseRedirect)
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.decorators import login_required

from dashboard.models import *
from dashboard.forms import HabitsPUCForm, create_detail_formset


@login_required()
def habitsandpractices(request, pk,
                      template_name='data_group/habitsandpractices.html'):
    doc = get_object_or_404(DataDocument, pk=pk, )
    script = Script.objects.get(title='Manual (dummy)', script_type='EX')
    extext, created = ExtractedText.objects.get_or_create(data_document=doc,
                                                    extraction_script=script)
    if created:
        extext.doc_date = 'please add...'
    ExtractedTextForm, HnPFormSet = create_detail_formset(doc)
    ext_form = ExtractedTextForm(request.POST or None, instance=extext)
    hp_formset = HnPFormSet(request.POST or None,
                            instance=extext, prefix='habits')
    if request.method == 'POST' and 'save' in request.POST:
        if hp_formset.is_valid() and ext_form.is_valid():
            if not doc.extracted:
                doc.extracted = True
                doc.save()
            hp_formset.save()
            ext_form.save()
            return HttpResponseRedirect(f'/habitsandpractices/{doc.pk}')
    context = {   'doc'         : doc,
                  'ext_form'    : ext_form,
                  'hp_formset'  : hp_formset,
                  }
    return render(request, template_name, context)


@login_required()
def link_habitsandpractices(request, pk,
                        template_name='data_group/habitsandpractices_to_puc.html'):
    hnp = get_object_or_404(ExtractedHabitsAndPractices, pk=pk, )
    form = HabitsPUCForm()
    if request.method == 'POST':
        form = HabitsPUCForm(request.POST)
        if form.is_valid():
            puc = PUC.objects.get(id=form['puc'].value())
            # make sure the PUC link doesn't already exist
            if not ExtractedHabitsAndPracticesToPUC.objects.filter(
                    PUC=puc,
                    extracted_habits_and_practices=hnp).exists():
                ExtractedHabitsAndPracticesToPUC.objects.create(
                        PUC=puc,
                        extracted_habits_and_practices=hnp
                )
                form = HabitsPUCForm()
    linked = ExtractedHabitsAndPracticesToPUC.objects.filter(
                    extracted_habits_and_practices=hnp).values('PUC')
    hnp_puc = PUC.objects.filter(pk__in=linked)
    print(hnp_puc)
    context = {'hnp': hnp,
                'form': form,
                'hnp_puc': hnp_puc,
    }
    return render(request, template_name, context)
