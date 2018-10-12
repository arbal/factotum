from django import forms
from django.conf import settings
from django.core.files import File
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from dashboard.models import (DSSToxSubstance)

@login_required()
def dsstox_substance_detail(request, pk,
                      template_name='chemicals/dsstox_substance_detail.html'):
    s = get_object_or_404(DSSToxSubstance, pk=pk, )
    return render(request, template_name, {'substance': s,  })
