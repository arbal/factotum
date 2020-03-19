from django_filters import rest_framework as filters

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


class ChemicalFilter(filters.FilterSet):
    puc = filters.NumberFilter(
        help_text="A PUC ID to filter chemicals against.",
        field_name="curated_chemical__extracted_text__data_document__product__puc__id",
        initial="1",
    )

    class Meta:
        model = models.DSSToxLookup
        fields = []
