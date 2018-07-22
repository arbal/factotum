
from django.shortcuts import render

def get_data(request, template_name='get_data/get_data.html'):

    return render(request, template_name)