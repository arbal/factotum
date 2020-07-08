from django.db.models import Value, IntegerField, Q
from django.shortcuts import render, get_object_or_404
from django.utils.html import format_html
from django_datatables_view.base_datatable_view import BaseDatatableView

from dashboard.models import DSSToxLookup, PUC, ProductDocument, PUCKind


def chemical_detail(request, sid, puc_id=None):
    chemical = get_object_or_404(DSSToxLookup, sid=sid)
    puc = get_object_or_404(PUC, id=puc_id) if puc_id else None
    keysets = chemical.get_tag_sets()
    group_types = chemical.get_unique_datadocument_group_types_for_dropdown()
    puc_kinds = PUCKind.objects.all()

    formulation_pucs = (
        PUC.objects.filter(kind__code="FO")
        .dtxsid_filter(sid)
        .with_num_products()
        .astree()
    )
    # get parent PUCs too
    formulation_pucs.merge(
        PUC.objects.all()
        .annotate(num_products=Value(0, output_field=IntegerField()))
        .astree()
    )
    # Get cumulative product count, displayed in bubble_puc_legend
    for puc_name, puc_obj in formulation_pucs.items():
        puc_obj.cumnum_products = sum(
            p.num_products for p in formulation_pucs.objects[puc_name].values()
        )

    article_pucs = (
        PUC.objects.filter(kind__code="AR")
        .dtxsid_filter(sid)
        .with_num_products()
        .astree()
    )
    # get parent PUCs too
    article_pucs.merge(
        PUC.objects.all()
        .annotate(num_products=Value(0, output_field=IntegerField()))
        .astree()
    )
    # Get cumulative product count, displayed in bubble_puc_legend
    for puc_name, puc_obj in article_pucs.items():
        puc_obj.cumnum_products = sum(
            p.num_products for p in article_pucs.objects[puc_name].values()
        )

    context = {
        "chemical": chemical,
        "keysets": keysets,
        "group_types": group_types,
        "formulation_pucs": formulation_pucs,
        "article_pucs": article_pucs,
        "puc": puc,
        "show_filter": True,
        "puc_kinds": puc_kinds,
    }
    return render(request, "chemicals/chemical_detail.html", context)


class ChemicalProductListJson(BaseDatatableView):
    model = ProductDocument
    columns = ["product", "document", "product.uber_puc", "product.uber_puc.kind.name"]

    def get_filter_method(self):
        return self.FILTER_ICONTAINS

    def get_initial_queryset(self):
        qs = super().get_initial_queryset()
        sid = self.request.GET.get("sid")
        if sid:
            return qs.filter(
                Q(document__extractedtext__rawchem__dsstox__sid=sid)
            ).distinct()
        return qs.filter()

    def render_column(self, row, column):
        value = self._render_column(row, column)
        if column == "product":
            return format_html(
                '<a href="{}" title="Go to Product detail" target="_blank">{}</a>',
                row.product.get_absolute_url(),
                value,
            )
        if column == "document":
            return format_html(
                '<a href="{}" title="Go to Document detail" target="_blank">{}</a>',
                row.document.get_absolute_url(),
                value,
            )
        if column == "product.uber_puc":
            value = self._render_column(row, column)
            if value and hasattr(row, "get_absolute_url"):
                return format_html(
                    '<a href="{}" title="Go to PUC detail" target="_blank">{}</a>',
                    row.product.uber_puc.get_absolute_url(),
                    value,
                )
        if column == "product.uber_puc.kind.name":
            value = self._render_column(row, column)
            if value and hasattr(row, "get_absolute_url"):
                return format_html("<p>{}</p>", value)
        return value

    def filter_queryset(self, qs):
        puc = self.request.GET.get("category")
        s = self.request.GET.get("search[value]", None)
        puc_kind = self.request.GET.get("puc_kind")
        if puc:
            qs = qs.filter(Q(product__puc=puc)).distinct()
        if s:
            qs = qs.filter(
                Q(product__title__icontains=s) | Q(document__title__icontains=s)
            ).distinct()
        if puc_kind and puc_kind != "all":
            if puc_kind == "none":
                qs = qs.filter(product__puc__isnull=True)
            else:
                qs = qs.filter(product__puc__kind__code=puc_kind)
        return qs
