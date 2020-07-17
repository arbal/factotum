from functools import partial

from django.core.validators import EMPTY_VALUES
from django_filters import rest_framework as filters
from rest_framework.exceptions import ValidationError

from dashboard import models


class EmptyStringFilter(filters.BooleanFilter):
    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs

        exclude = self.exclude ^ (value is False)
        method = qs.exclude if exclude else qs.filter

        return method(**{self.field_name: ""})


class PUCFilter(filters.FilterSet):
    chemical = filters.NumberFilter(
        help_text="A chemical id to filter products against.",
        field_name="products__datadocument__extractedtext__rawchem__dsstox__pk",
        initial="DTXSID6026296",
    )

    sid = filters.CharFilter(
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
    sid = filters.CharFilter(
        help_text="A chemical DTXSID to filter products against.",
        field_name="documents__extractedtext__rawchem__dsstox__sid",
        initial="DTXSID6026296",
    )

    chemical = filters.NumberFilter(
        help_text="A chemical id to filter products against.",
        field_name="documents__extractedtext__rawchem__dsstox",
        initial=1,
    )

    upc = filters.CharFilter(
        help_text="A Product UPC to filter products against.", initial="stub_47"
    )

    class Meta:
        model = models.Product
        fields = []


class FunctionalUseFilter(filters.FilterSet):
    data_document = filters.NumberFilter(
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


class ChemicalFilter(filters.FilterSet):
    puc = filters.NumberFilter(
        help_text="A PUC ID to filter chemicals against.",
        label="PUC",
        field_name="curated_chemical__extracted_text__data_document__product__puc__id",
        initial="1",
    )
    sid = filters.CharFilter(
        field_name="sid", label="sid", help_text="A SID to filter chemicals against."
    )

    class Meta:
        model = models.DSSToxLookup
        fields = []


class ChemicalInstanceFilter(filters.FilterSet):
    chemical = filters.NumberFilter(
        help_text="A chemical ID to filter chemicals against.",
        label="chemical_id",
        field_name="dsstox__pk",
    )
    sid = filters.CharFilter(
        field_name="dsstox__sid",
        label="sid",
        help_text="A SID to filter chemicals against.",
    )
    rid__isnull = EmptyStringFilter(field_name="rid")

    class Meta:
        model = models.RawChem
        fields = ["rid"]


class ChemicalPresenceTagsetFilter(filters.FilterSet):
    chemical = filters.CharFilter(field_name="sid", distinct=True)
    keyword = filters.NumberFilter(
        field_name="curated_chemical__extractedlistpresence__tags__pk", distinct=True
    )
    data_document = filters.NumberFilter(
        field_name="curated_chemical__extracted_text__data_document_id", distinct=True
    )

    def filter_queryset(self, queryset):
        if not set(self.request.GET.keys() & self.form.fields.keys()):
            raise ValidationError(
                "Request must be filtered by one of these parameters "
                "['chemical', 'document', 'keyword']"
            )
        queryset = super().filter_queryset(queryset)
        for item in queryset:
            item.tagsets = partial(
                item.get_tags_with_extracted_text,
                tag_id=self.form.cleaned_data.get("keyword"),
                doc_id=self.form.cleaned_data.get("document"),
            )
        return queryset


class ChemicalPresenceFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name")
    definition = filters.CharFilter(field_name="definition")
    kind = filters.CharFilter(field_name="kind__name")


class CompositionFilter(filters.FilterSet):
    data_document = filters.NumberFilter(
        field_name="extracted_text__data_document_id",
        help_text="Document ID to filter composition data against.",
        initial=100000,
    )
    sid = filters.CharFilter(
        field_name="dsstox__sid",
        help_text="Chemical sid to filter composition data against.",
        initial="DTXSID9022528",
    )
    chemical = filters.NumberFilter(
        field_name="dsstox__pk",
        help_text="Chemical id to filter composition data against.",
        initial=100000,
    )
    rid = filters.CharFilter(
        field_name="rid",
        help_text="Composition's rid to filter composition data against.",
        initial="DTXRID001",
    )
    product = filters.NumberFilter(
        field_name="extracted_text__data_document__products__pk",
        help_text="Product id to filter composition data against.",
        initial=100000,
    )
