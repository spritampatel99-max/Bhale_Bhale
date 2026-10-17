"""Custom error pages."""
from django.shortcuts import render
from django.template import loader
from django.http import HttpResponseServerError


def error_403(request, exception=None):
    return render(request, "errors/403.html", status=403)


def error_404(request, exception=None):
    return render(request, "errors/404.html", status=404)


def error_500(request):
    # Standalone template: must not depend on the database or context processors.
    return HttpResponseServerError(loader.render_to_string("errors/500.html"))
