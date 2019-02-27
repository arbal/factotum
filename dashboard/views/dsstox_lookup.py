from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404

from dashboard.models import (DSSToxLookup)

@login_required()
def dsstox_lookup_detail(request, pk,
                      template_name='chemicals/dsstox_lookup_detail.html'):
    s = get_object_or_404(DSSToxLookup, pk=pk, )
    return render(request, template_name, {'substance': s,  })
