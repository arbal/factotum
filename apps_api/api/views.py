import operator
import types

from django.db.models import Prefetch, Q
from django.template.defaultfilters import pluralize
from django.utils.datastructures import MultiValueDict
from django_filters.rest_framework import DjangoFilterBackend
from django_mysql.models import add_QuerySetMixin
from rest_framework import viewsets, generics, permissions, status
from rest_framework.exceptions import NotFound
from rest_framework.renderers import BrowsableAPIRenderer, JSONRenderer
from rest_framework.response import Response
from rest_framework.viewsets import ViewSetMixin
from rest_framework.mixins import CreateModelMixin
from rest_framework_json_api.views import RelationshipView, ModelViewSet

from apps_api.api import filters, serializers
from dashboard import models
from dashboard.forms.data_group import ProductBulkCSVFormSet
from dashboard.utils import gather_errors


class PUCViewSet(ModelViewSet):
    """
    Service providing a list of all Product Use Categories (PUCs) in ChemExpoDB.
    The PUCs follow a three-tiered hierarchy (Levels 1-3) for categorizing products.
    Every combination of Level 1-3 categories is unique, and the combination of Level 1, Level 2,
    and Level 3 categories together define the PUCs. Additional information on PUCs can be found in
    Isaacs, 2020. https://www.nature.com/articles/s41370-019-0187-5
    """

    http_method_names = ["get", "head", "options"]
    serializer_class = serializers.PUCSerializer
    queryset = models.PUC.objects.all().order_by("id")
    filterset_class = filters.PUCFilter


class ProductViewSet(ModelViewSet, CreateModelMixin):
    """
    list: Service providing a list of all products in ChemExpoDB, along with metadata
    describing the product. In ChemExpoDB, a product is defined as an item having a
    unique UPC. Thus the same formulation (i.e., same chemical composition) may be
    associated with multiple products, each having their own UPC (e.g., different size
    bottles of a specific laundry detergent all have the same chemical make-up, but
    have different UPCs).
    """

    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    http_method_names = ["get", "post", "head", "options"]
    serializer_class = serializers.ProductSerializer
    queryset = models.Product.objects.prefetch_pucs().prefetch_related(
        Prefetch("documents", queryset=models.DataDocument.objects.order_by("id"))
    )
    filterset_class = filters.ProductFilter

    def create_bulk(self, request, *args, **kwargs):
        """Custom endpoint specifically for CSV uploads.  Uses ProductBulkCSVFormSet.
        accepts body files for csv and images and return a 204 on success
        """
        management_form = {
            "products-TOTAL_FORMS": "1",
            "products-INITIAL_FORMS": "0",
            "products-MAX_NUM_FORMS": "",
        }
        files = self._translate_files(request.FILES)
        form = ProductBulkCSVFormSet(management_form, files)
        if form.is_valid():
            num_saved = form.save()
            return Response(
                {
                    "message": "%d product%s created successfully."
                    % (num_saved[0], pluralize(num_saved[0]))
                },
                status=status.HTTP_202_ACCEPTED,
            )

        errors = gather_errors(form)
        error_list = []
        for e in errors:
            error_list.append(e)
        return Response(
            [
                {"detail": error, "status": status.HTTP_400_BAD_REQUEST}
                for error in error_list
            ],
            status=status.HTTP_400_BAD_REQUEST,
        )

    def _translate_files(self, request_files):
        """Copy the files dictionary into an identical dictionary with
        the less user friendly names
        """
        filemap = {
            "csv": "products-bulkformsetfileupload",
            "images": "products-bulkformsetimageupload",
        }
        files_dict = {}
        for name in request_files:
            if name in filemap.keys():
                files_dict.update({filemap.get(name): request_files.getlist(name)})
        return MultiValueDict(files_dict)


class DocumentViewSet(ModelViewSet):
    """
    list: Service providing a list of all documents in ChemExpoDB, along with
    metadata describing the document. Service also provides the actual data
    points found in, and extracted from, the document. e.g., chemicals and their
    weight fractions may be included for composition documents.
    """

    http_method_names = ["get", "head", "options"]
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


class DocumentRelationshipView(RelationshipView):
    http_method_names = ["get", "head", "options"]
    queryset = models.DataDocument.objects
    field_name_mapping = {
        "products": "products",
        "chemicals": "extractedtext.rawchem.select_subclasses",
    }

    def get_related_instance(self):
        try:
            value = operator.attrgetter(self.get_related_field_name())(
                self.get_object()
            )
            # Check to see if mapping is to a method.  If so evaluate. (Specifically for select_subclasses)
            if isinstance(value, types.MethodType):
                return value()
            return value
        except AttributeError:
            raise NotFound


class ChemicalViewSet(viewsets.ReadOnlyModelViewSet):
    """
    list: Service providing a list of all registered chemical
    substances linked to data in ChemExpoDB. All chemical data in
    ChemExpoDB is linked by the DTXSID, or the unique structure based
    identifier for the chemical substance. Service provides the DTXSID,
    preferred chemical name, and preferred CAS.
    """

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
    filterset_class = filters.ChemicalPresenceFilter
    filterset_fields = {"name", "definition", "kind"}


class FunctionalUseViewSet(ModelViewSet):
    """
    list: Service to retrieve the functional use to chemical connection.
    Query parameter is required, which can be any of ["document", "chemical", "category"]
    """

    http_method_names = ["get", "head", "options"]
    serializer_class = serializers.FunctionalUseSerializer
    queryset = models.FunctionalUse.objects.prefetch_related(
        "chem__extracted_text__data_document", "chem__dsstox"
    ).order_by("id")
    filterset_class = filters.FunctionalUseFilter


class FunctionalUseRelationshipView(RelationshipView):
    http_method_names = ["get", "head", "options"]
    queryset = models.FunctionalUse.objects
    field_name_mapping = {
        "chemical": "chem.dsstox",
        "dataDocument": "chem.extracted_text.data_document",
    }

    def get_related_instance(self):
        try:
            return operator.attrgetter(self.get_related_field_name())(self.get_object())
        except AttributeError:
            raise NotFound


class FunctionUseCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    list: Service providing a list of all functional use categories.
    """

    serializer_class = serializers.FunctionalUseCategorySerializer
    queryset = models.FunctionalUseCategory.objects.all().order_by("id")
    filterset_fields = {"title", "description"}


class ChemicalPresenceTagViewSet(ViewSetMixin, generics.ListAPIView):
    """
    list: Service returns all chemicals and their associated tags, documents, and rids.
    Accepts a required filter for any of ["chemical", "document", "keyword"]
    """

    serializer_class = serializers.ChemicalPresenceTagsetSerializer
    queryset = models.DSSToxLookup.objects.all().order_by("id")
    filterset_class = filters.ChemicalPresenceTagsetFilter
    # Todo:  These are using the default DRF filters and renderer backends.
    #  These should be removed as the route is made jsonapi compliant
    filter_backends = [DjangoFilterBackend]
    renderer_classes = [JSONRenderer, BrowsableAPIRenderer]


class CompositionViewSet(ModelViewSet):
    """
    Service providing all Composition data in ChemExpoDB.
    """

    http_method_names = ["get", "head", "options"]
    serializer_class = serializers.ExtractedChemicalSerializer
    queryset = (
        models.ExtractedChemical.objects.all()
        .exclude(Q(dsstox__isnull=True) | Q(rid__isnull=True) | Q(rid=""))
        .prefetch_related("extracted_text__data_document__products", "dsstox")
        .order_by("id")
    )
    filterset_class = filters.CompositionFilter


class ExtractedChemicalRelationshipView(RelationshipView):
    http_method_names = ["get", "head", "options"]
    queryset = models.ExtractedChemical.objects
    field_name_mapping = {
        "chemical": "dsstox",
        "dataDocument": "extracted_text.data_document",
        "products": "extracted_text.data_document.products",
    }

    def get_related_instance(self):
        try:
            return operator.attrgetter(self.get_related_field_name())(self.get_object())
        except AttributeError:
            raise NotFound


class RawChemViewSet(ViewSetMixin, generics.ListAPIView):
    """
    list: Service providing RawChem resources related to a dataDocument resource.
    """

    serializer_class = serializers.ExtractedChemicalSerializer
    queryset = (
        models.RawChem.objects.all()
        .exclude(Q(dsstox__isnull=True) | Q(rid__isnull=True) | Q(rid=""))
        .prefetch_related("dsstox")
        .order_by("id")
    )


class RawChemRelationshipView(RelationshipView):
    http_method_names = ["get", "head", "options"]
    queryset = models.RawChem.objects.exclude(
        Q(dsstox__isnull=True) | Q(rid__isnull=True) | Q(rid="")
    )
    field_name_mapping = {
        "chemical": "dsstox",
        "dataDocument": "extracted_text.data_document",
    }

    def get_related_instance(self):
        try:
            return operator.attrgetter(self.get_related_field_name())(self.get_object())
        except AttributeError:
            raise NotFound
