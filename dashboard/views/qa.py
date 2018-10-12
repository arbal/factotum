from django.forms import ModelForm, Form, BaseInlineFormSet, inlineformset_factory, TextInput, CharField

from django.shortcuts import render, redirect, get_object_or_404

from django.contrib.auth.decorators import login_required

from dashboard.models import Script

# we are not currently using this class



@login_required()
def qa_index(request, template_name='qa/qa_index.html'):

    scripts = Script.objects.filter(script_type='EX')
    return render(request, template_name, {'extraction_scripts': scripts})
