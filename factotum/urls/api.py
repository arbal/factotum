from django.conf.urls import url
from django.urls import path, include

from apps_api.core import views as coreviews
from apps_api.api import views as apiviews
from apps_api.core.routers import CustomRelationRouter
from apps_api.openapi import views as docsviews
from factotum import settings


router = CustomRelationRouter()

router.register(r"pucs", apiviews.PUCViewSet, basename="puc")
router.register(r"products", apiviews.ProductViewSet)
router.register(r"dataGroups", apiviews.DataGroupViewSet, basename="dataGroup")
router.register(r"dataSources", apiviews.DataSourceViewSet, basename="dataSource")
router.register(r"dataDocuments", apiviews.DocumentViewSet, basename="dataDocument")
router.register(r"chemicals", apiviews.ChemicalViewSet)
router.register(
    r"chemicalInstances", apiviews.ChemicalInstanceViewSet, basename="chemicalInstance"
)
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
router.register(r"compositions", apiviews.CompositionViewSet, basename="composition")
router.register(
    r"classificationMethods",
    apiviews.ClassificationMethodViewSet,
    basename="classificationMethod",
)

router.register(r"productToPucs", apiviews.ProductToPucViewSet, basename="productToPuc")

urlpatterns = [
    path("openapi.json/", docsviews.OpenAPIView.as_view(), name="openapi-schema"),
    path("token/", coreviews.ObtainExpiringAuthToken.as_view(), name="token"),
    path("", include(router.urls)),
    path("", docsviews.RedocView.as_view()),
    # Relationships endpoints
    path(
        "functionalUses/<pk>/relationships/<related_field>",
        view=apiviews.FunctionalUseRelationshipView.as_view(),
        name="functionalUse-relationships",
    ),
    path(
        "dataDocuments/<pk>/relationships/<related_field>",
        view=apiviews.DocumentRelationshipView.as_view(),
        name="dataDocument-relationships",
    ),
    path(
        "dataGroups/<pk>/relationships/<related_field>",
        view=apiviews.DataGroupRelationshipView.as_view(),
        name="dataGroup-relationships",
    ),
    # Relationships endpoints chemicalInstance
    #  For clarity the urls are going to be different but the RelationshipView
    #  functions the same for all children of the raw chemical model
    path(
        "compositions/<pk>/relationships/<related_field>",
        view=apiviews.ChemicalInstanceRelationshipView.as_view(),
        name="composition-relationships",
    ),
    path(
        "chemicalInstances/<pk>/relationships/<related_field>",
        view=apiviews.ChemicalInstanceRelationshipView.as_view(),
        name="chemicalInstance-relationships",
    ),
    # Custom viewset actions
    path(
        "products/bulk",
        view=apiviews.ProductViewSet.as_view(actions={"post": "create_bulk"}),
        name="product_csv",
    ),
    path(
        "products",
        view=apiviews.ProductViewSet.as_view(actions={"post": "create"}),
        name="product",
    ),
    path(
        "products/<pk>/relationships/<related_field>",
        view=apiviews.ProductRelationshipView.as_view(),
        name="product-relationships",
    ),
    path(
        "productToPucs/<pk>/relationships/<related_field>",
        view=apiviews.ProductToPucRelationshipView.as_view(),
        name="productToPuc-relationships",
    ),
    path("", include("django_prometheus.urls")),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [url(r"^__debug__/", include(debug_toolbar.urls))] + urlpatterns
