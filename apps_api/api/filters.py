from django_filters import rest_framework as filters
from rest_framework.exceptions import ValidationError

from dashboard import models


class PUCFilter(filters.FilterSet):
    chemical = filters.CharFilter(
        help_text="A chemical DTXSID to filter products against.",
        method="dtxsid_filter",
        initial="DTXSID6026296",
    )

    def dtxsid_filter(self, queryset, name, value):
        return queryset.dtxsid_filter(value)

    class Meta:
        model = models.PUC
        fields = []


class ProductFilter(filters.FilterSet):
    chemical = filters.CharFilter(
        help_text="A chemical DTXSID to filter products against.",
        field_name="documents__extractedtext__rawchem__dsstox__sid",
        initial="DTXSID6026296",
    )

    upc = filters.CharFilter(
        help_text="A Product UPC to filter products against.", initial="stub_47"
    )

    class Meta:
        model = models.Product
        fields = []


class FunctionalUseFilter(filters.FilterSet):
    document = filters.NumberFilter(
        field_name="chem__extracted_text__data_document_id",
        help_text="Document ID to filter the functional use against",
        initial="156051",
    )
    chemical = filters.CharFilter(
        field_name="chem__dsstox__sid",
        help_text="Chemical SID to filter the functional use against",
        initial="DTXSID9022528",
    )
    category = filters.NumberFilter(
        field_name="category",
        help_text="Functional Use Category ID to filter the functional use against",
        initial="1",
    )

    class Meta:
        model = models.FunctionalUse
        fields = []

    def is_valid(self):
        if not set(self.request.GET.keys() & self.form.fields.keys()):
            raise ValidationError(
                "Request must be filtered by one of these parameters "
                "['document', 'chemical', 'category']"
            )
        return super().is_valid()


class ChemicalFilter(filters.FilterSet):
    puc = filters.NumberFilter(
        help_text="A PUC ID to filter chemicals against.",
        field_name="curated_chemical__extracted_text__data_document__product__puc__id",
        initial="1",
    )

    class Meta:
        model = models.DSSToxLookup
        fields = []


class CompositionFilter(filters.FilterSet):
    document = filters.NumberFilter(
        field_name="extracted_text__data_document_id",
        help_text="Document ID to filter composition data against.",
        initial=100000,
    )
    chemical = filters.CharFilter(
        field_name="dsstox__sid",
        help_text="Chemical sid to filter composition data against.",
        initial="DTXSID9022528",
    )
    rid = filters.CharFilter(
        field_name="rid",
        help_text="Composition's rid to filter composition data against.",
        initial="DTXRID001",
    )
    product = filters.NumberFilter(
        field_name="extracted_text__data_document__products",
        help_text="Product id to filter composition data against.",
        initial=100000,
    )

    def is_valid(self):
        if not set(self.request.GET.keys() & self.form.fields.keys()):
            raise ValidationError(
                "Request must be filtered by one of these parameters "
                "['rid', 'product', 'chemical', 'document']"
            )
        return super().is_valid()
