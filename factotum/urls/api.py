from django.conf.urls import url
from django.urls import path, include

from apps_api.api import views as apiviews
from apps_api.core.routers import CustomRelationRouter
from apps_api.openapi import views as docsviews
from factotum import settings


router = CustomRelationRouter()

router.register(r"pucs", apiviews.PUCViewSet)
router.register(r"products", apiviews.ProductViewSet)
router.register(r"dataDocuments", apiviews.DocumentViewSet, basename="dataDocument")
router.register(r"chemicals", apiviews.ChemicalViewSet)
router.register(
    r"chemicalpresences",
    apiviews.ChemicalPresenceViewSet,
    basename="chemical_presences",
)
router.register(
    r"functionalUses", apiviews.FunctionalUseViewSet, basename="functionalUse"
)
router.register(r"functionalUseCategories", apiviews.FunctionUseCategoryViewSet)
router.register(r"chemicalpresence", apiviews.ChemicalPresenceTagViewSet)
router.register(r"composition", apiviews.CompositionViewSet)

urlpatterns = [
    path("openapi.json/", docsviews.OpenAPIView.as_view(), name="openapi-schema"),
    path("", include(router.urls)),
    path("", docsviews.RedocView.as_view()),
    # Relationships endpoints
    path(
        "functionalUses/<pk>/relationships/<related_field>",
        view=apiviews.FunctionalUseRelationshipView.as_view(),
        name="functionalUse-relationships",
    ),
    path(
        "dataDocuments/<pk>/chemicals/<related_field>",
        view=apiviews.RawChemRelationshipView.as_view(),
        name="dataDocument-relationships",
    ),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [url(r"^__debug__/", include(debug_toolbar.urls))] + urlpatterns
