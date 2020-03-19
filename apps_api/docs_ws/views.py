from django.views.generic.base import TemplateView
from rest_framework import permissions

from drf_yasg.views import get_schema_view
from drf_yasg import openapi


class ReDocView(TemplateView):
    template_name = "docs/redoc.html"


SchemaView = get_schema_view(
    openapi.Info(
        title="Factotum Web Services",
        default_version="v0",
        description=(
            "The Factotum Web Services API is a service that provides data "
            "about Product Usage Category (PUC), consumer products, and the chemicals related "
            "to PUCs and products."
        ),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)
