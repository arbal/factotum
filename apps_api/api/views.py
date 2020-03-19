from django.db.models import Prefetch
from rest_framework import viewsets

from apps_api.api import filters, serializers
from dashboard import models
from django_mysql.models import add_QuerySetMixin


class PUCViewSet(viewsets.ReadOnlyModelViewSet):
    """
    list: Service providing a list of all Product Use Categories (PUCs) in ChemExpoDB.
    The PUCs follow a three-tiered hierarchy (Levels 1-3) for categorizing products.
    Every combination of Level 1-3 categories is unique, and the combination of Level 1, Level 2,
    and Level 3 categories together define the PUCs. Additional information on PUCs can be found in
    <a href="https://www.nature.com/articles/s41370-019-0187-5" target="_blank">Isaacs, 2020</a>.
    """

    serializer_class = serializers.PUCSerializer
    queryset = models.PUC.objects.all().order_by("id")
    filterset_class = filters.PUCFilter


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    list: Service providing a list of all products in ChemExpoDB, along with metadata
    describing the product. In ChemExpoDB, a product is defined as an item having a
    unique UPC. Thus the same formulation (i.e., same chemical composition) may be
    associated with multiple products, each having their own UPC (e.g., different size
    bottles of a specific laundry detergent all have the same chemical make-up, but
    have different UPCs).
    """

    serializer_class = serializers.ProductSerializer
    queryset = models.Product.objects.prefetch_pucs().prefetch_related(
        Prefetch("documents", queryset=models.DataDocument.objects.order_by("id"))
    )
    filterset_class = filters.ProductFilter


class DocumentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    list: Service providing a list of all documents in ChemExpoDB, along with
    metadata describing the document. Service also provides the actual data
    points found in, and extracted from, the document. e.g., chemicals and their
    weight fractions may be included for composition documents.
    """

    serializer_class = serializers.DocumentSerializer
    # By using the STRAIGHT_JOIN directive, the query time is reduced
    # from >2 seconds to ~0.0005 seconds. Pretty big! This is due to
    # poor MySQL optimization with INNER JOIN and ORDER BY.
    queryset = (
        add_QuerySetMixin(models.DataDocument.objects.all())
        .prefetch_related(
            Prefetch(
                "extractedtext__rawchem",
                queryset=models.RawChem.objects.filter(dsstox__isnull=False)
                .select_related("dsstox")
                .select_subclasses(),
            ),
            Prefetch("products"),
        )
        .straight_join()
        .select_related("data_group__group_type", "document_type")
        .order_by("-id")
    )


class ChemicalViewSet(viewsets.ReadOnlyModelViewSet):
    """
    list: Service providing a list of all registered chemical
    substances linked to data in ChemExpoDB. All chemical data in
    ChemExpoDB is linked by the DTXSID, or the unique structure based
    identifier for the chemical substance. Service provides the DTXSID,
    preferred chemical name, and preferred CAS.
    """

    lookup_field = "sid"
    lookup_url_kwarg = "id"
    serializer_class = serializers.ChemicalSerializer
    queryset = models.DSSToxLookup.objects.exclude(
        curated_chemical__isnull=True
    ).order_by("sid")
    filterset_class = filters.ChemicalFilter


class ChemicalPresenceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    list: Service providing a list of all chemical presence tags in ChemExpoDB.
    A 'tag' (or keyword) may be applied to a chemical, indicating that there
    exists data in ChemExpoDB providing evidence that a chemical is related to
    that tag. Multiple tags may be applied to a single source-chemical instance,
    in which case the tags should be interpreted as a group.
    """

    serializer_class = serializers.ChemicalPresenceSerializer
    queryset = (
        models.ExtractedListPresenceTag.objects.all()
        .select_related("kind")
        .order_by("id")
    )
