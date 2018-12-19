from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from dashboard.models import PUC
from django.db.models import Count

def puc_list(request, template_name='puc/puc_list.html'):
    pucs = PUC.objects.all().annotate(num_products=Count('products'))
    data = {}
    data['pucs'] = pucs
    return render(request, template_name, data)