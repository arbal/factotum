from django.shortcuts import render


def error_handler(request, status):
    return render(request, "core/error.html", {"status": status})


def error_handler401(request):
    return render(request, "core/error.html", {"status": 401})


def error_handler403(request, exception):
    return render(request, "core/error.html", {"status": 403})


def error_handler404(request, exception):
    return render(request, "core/error.html", {"status": 404})


def error_handler500(request):
    return render(request, "core/error.html", {"status": 500})
