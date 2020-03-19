from django.conf.urls import url
from django.urls import path, include
from rest_framework import routers


from apps_api.api import views as apiviews
from apps_api.docs_ws import views as docsviews
from factotum import settings

router = routers.SimpleRouter()
router.register(r"pucs", apiviews.PUCViewSet)
router.register(r"products", apiviews.ProductViewSet)
router.register(r"documents", apiviews.DocumentViewSet)
router.register(r"chemicals", apiviews.ChemicalViewSet)
router.register(
    r"chemicalpresences",
    apiviews.ChemicalPresenceViewSet,
    basename="chemical_presences",
)

urlpatterns = [
    path(
        "openapi/",
        docsviews.SchemaView.without_ui(cache_timeout=0),
        name="openapi-schema",
    ),
    path("", include(router.urls)),
    path("", docsviews.ReDocView.as_view()),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [url(r"^__debug__/", include(debug_toolbar.urls))] + urlpatterns
