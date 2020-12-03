from django.shortcuts import render

def handler401(request):
    return render(request, 'core/error.html', status=401)

def handler403(request, exception):
    return render(request, 'core/error.html', status=403)

def handler404(request, exception):
    return render(request, 'core/error.html', status=404)

def handler500(request):
    return render(request, 'core/error.html', status=500)