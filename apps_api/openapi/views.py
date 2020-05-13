import os

from django.http import HttpResponse
from django.views.generic.base import TemplateView, View

import _jsonnet as jsonnet


class RedocView(TemplateView):
    """The Redoc documentation."""

    template_name = "redoc.html"


class OpenAPIView(View):
    """The OpenAPI spec file."""

    http_method_names = ["get"]

    base_spec = jsonnet.evaluate_file(
        os.path.join(os.path.dirname(__file__), "schemas", "schema.jsonnet"),
        ext_vars={"baseServer": "__BASE_SERVER__"},
    )

    def get(self, request, *args, **kwargs):
        return HttpResponse(self.base_spec, content_type="application/json")
