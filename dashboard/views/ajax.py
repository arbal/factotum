from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic.detail import SingleObjectMixin
from django_datatables_view.base_datatable_view import BaseDatatableView
from django.http import JsonResponse
from django.db.models import Q, Count, Subquery, Case, When, F, Value, CharField
from django.utils.html import format_html
from django.views.decorators.cache import cache_page
from django.template.defaultfilters import truncatechars
from dashboard.utils import GroupConcat

from dashboard.models import (
    Product,
    ProductToPUC,
    GroupType,
    DataDocument,
    DSSToxLookup,
    RawChem,
    ExtractedCPCat,
    ExtractedListPresence,
    ExtractedListPresenceToTag,
    ExtractedListPresenceTag,
    FunctionalUseToRawChem,
)


class FilterDatatableView(BaseDatatableView):
    def get_filter_method(self):
        return self.FILTER_ICONTAINS


class PucFunctionalUseListJson(BaseDatatableView):
    """
    Provides JSON elements describing each functional use that appears in each 
    document associated via Product to the detail page's PUC as the uberpuc.
    """

    model = FunctionalUseToRawChem
    columns = [
        "chemical.extracted_text.data_document.title",  # DataDocument title with link to detail page
        "preferred_name",  # Preferred chemical name
        "preferred_cas",  # Preferred CAS
        "functional_use.report_funcuse",  # Reported Functional Use
        "functional_use.category.title",  # Harmonized Functional Use
    ]

    def get_initial_queryset(self):
        qs = (
            super()
            .get_initial_queryset()
            .annotate(
                preferred_name=Case(
                    # no dsstox
                    When(
                        chemical__dsstox__isnull=False,
                        then=F("chemical__dsstox__true_chemname"),
                    ),
                    # not blank raw_chem_name
                    When(
                        ~Q(chemical__raw_chem_name=""),
                        then=F("chemical__raw_chem_name"),
                    ),
                    # no true chem no raw_chem_name
                    default=Value("Unnamed Chemical"),
                ),
                preferred_cas=Case(
                    # no dsstox
                    When(
                        chemical__dsstox__isnull=False,
                        then=F("chemical__dsstox__true_cas"),
                    ),
                    # not blank raw_chem_name
                    When(~Q(chemical__raw_chem_name=""), then=F("chemical__raw_cas")),
                    # no true chem no raw_chem_name
                    default=Value(""),
                ),
            )
            .select_related(
                "functional_use__category",
                "chemical__extracted_text__data_document",
                "chemical__dsstox",
                "chemical__dsstox",
            )
        )
        puc_id = self.request.GET.get("puc")

        if puc_id:
            return qs.filter(
                Q(
                    chemical__extracted_text__data_document__product__product_uber_puc__puc_id=puc_id
                )
            ).distinct()
        return qs

    def render_column(self, row, column):
        value = self._render_column(row, column)
        if column == "chemical.extracted_text.data_document.title":
            return format_html(
                '<a href="{}" title="Go to Document detail" target="_blank">{}</a>',
                row.chemical.extracted_text.data_document.get_absolute_url(),
                value,
            )
        return value


class ProductListJson(FilterDatatableView):
    """
    Provides JSON elements describing each Product related to 
    the detail page's PUC as the uberpuc.
    """

    model = Product
    columns = ["title", "brand_name", "product_uber_puc.classification_method.name"]

    def render_column(self, row, column):
        value = self._render_column(row, column)
        if column == "title":
            return format_html(
                '<a href="{}" title="Go to Product detail" target="_blank">{}</a>',
                row.get_absolute_url(),
                value,
            )
        return value

    def get_initial_queryset(self):
        qs = super().get_initial_queryset()
        puc = self.request.GET.get("puc")
        if puc:
            return qs.filter(Q(product_uber_puc__puc=puc))
        return qs


class DocumentListJson(FilterDatatableView):
    """
    Provides JSON elements describing each document with products assigned
    to the page's PUC as uberpuc
    """

    model = DataDocument
    columns = ["title", "data_group.group_type.title"]

    def get_initial_queryset(self):
        qs = super().get_initial_queryset()
        puc = self.request.GET.get("puc")
        sid = self.request.GET.get("sid")
        if puc:
            return qs.filter(Q(products__product_uber_puc__puc=puc)).distinct()
        if sid:
            return qs.filter(Q(extractedtext__rawchem__dsstox__sid=sid)).distinct()
        return qs

    def render_column(self, row, column):
        value = self._render_column(row, column)
        chem = self.request.GET.get("chem_detail")
        if column == "title":
            if chem:
                value = truncatechars(value, 50)
            return format_html(
                '<a href="{}" title="Go to Document detail" target="_blank">{}</a>',
                row.get_absolute_url(),
                value,
            )
        return value

    def filter_queryset(self, qs):
        qs = super().filter_queryset(qs)
        puc = self.request.GET.get("category")
        pid = self.request.GET.get("pid")
        group_type = self.request.GET.get("group_type")
        if puc:
            qs = qs.filter(Q(products__product_uber_puc__puc=puc))
        if group_type:
            if group_type != "-1":
                qs = qs.filter(data_group__group_type__id=group_type)
        if pid:
            ep = ExtractedListPresence.objects.get(pk=pid)
            lp_querysets = []
            for tag_pk in ep.tags.values_list("pk", flat=True):
                ids = ExtractedListPresenceToTag.objects.filter(
                    tag__id=tag_pk
                ).values_list("content_object", flat=True)
                lp_querysets.append(ExtractedListPresence.objects.filter(pk__in=ids))
            cleaned = ExtractedListPresence.objects.filter(pk__in=ids)
            # do an intersection of all chemicals w/ each tag
            for lp_qs in lp_querysets:
                cleaned &= lp_qs
            doc_ids = cleaned.values_list("extracted_text_id", flat=True)
            qs = qs.filter(pk__in=doc_ids)
        return qs


class ChemicalListJson(FilterDatatableView):
    """
    Provides JSON elements describing each curated chemical that is 
    associated via Product to the detail page's PUC as the uberpuc.
    """

    model = DSSToxLookup
    columns = ["sid", "true_cas", "true_chemname", "raw_count"]

    def get_initial_queryset(self):
        qs = super().get_initial_queryset()
        puc = self.request.GET.get("puc")
        if puc:
            qs = qs.filter(
                curated_chemical__extracted_text__data_document__product__product_uber_puc__puc=puc
            )
        return qs.annotate(raw_count=Count("curated_chemical"))

    def render_column(self, row, column):
        value = self._render_column(row, column)
        if value and hasattr(row, "get_absolute_url"):
            if column == "true_chemname":
                return format_html(truncatechars(value, 89))
            if column == "raw_count":
                return value
            return format_html(
                '<a href="{}" title="Go to Chemical detail" target="_blank">{}</a>',
                row.get_absolute_url(),
                value,
            )
        return value

    def filter_queryset(self, qs):
        s = self.request.GET.get("search[value]", None)
        if s:
            qs = qs.filter(
                Q(true_cas__icontains=s) | Q(true_chemname__icontains=s)
            ).distinct()
        return qs


class ListPresenceTagSetsJson(SingleObjectMixin, View):
    """
    Provides JSON elements describing each distinct combination of tags
    that a tag appears in.
    """

    model = ExtractedListPresenceTag

    def get(self, request, *args, **kwargs):
        tagsets = self.get_object().get_tagsets()
        tagsets_list = []
        for tagset in tagsets:
            tagset_names = []
            for tag in sorted(tagset, key=lambda o: o.name.lower()):
                tagset_names.append(
                    f"<a href='{reverse('lp_tag_detail', args=[tag.id])}' title='{tag.definition or 'No Definition'}'>{tag.name}</a>"
                )
            tagsets_list.append([" ; ".join(tagset_names)])
        return JsonResponse({"data": sorted(tagsets_list)}, safe=False)


class ListPresenceDocumentsJson(BaseDatatableView):
    """
    This view returns all the ExtractedCPCat documents where at least one 
    ExtractedListPresence child record has been associated with the list 
    presence tag identified by the "tag_pk" id argument.
    Along with each ExtractedCPCat record, it returns the unique tags related
    to that document's child records.
    """

    model = ExtractedCPCat
    columns = ["data_document.title", "tags"]

    def get_initial_queryset(self):
        qs = self.model.objects.filter(
            rawchem__extractedlistpresence__tags__pk=self.kwargs["tag_pk"]
        ).distinct()
        return qs

    def render_column(self, row, column):
        if column == "data_document.title":
            return f"<a href='{reverse('data_document', args=[row.data_document.id])}' title={row}'>{row}</a>"
        if column == "tags":
            tag_str_list = []
            tags = (
                ExtractedListPresenceTag.objects.filter(
                    extractedlistpresence__extracted_text__data_document=row.data_document_id
                )
                .order_by("name")
                .distinct()
            )
            for tag in tags:
                tag_str_list.append(
                    f"<a href='{reverse('lp_tag_detail', args=[tag.id])}' title='{tag.definition or 'No Definition'}'>{tag.name.lower()}</a>"
                )
            return " ; ".join(tag_str_list)
        return super().render_column(row, column)


@cache_page(86400)
def sids_by_grouptype_ajax(request):
    """Counts the number of DTXSIDs per GroupType. Multiple
    GroupTypes can be associated with a single DTXSID. The
    GroupType set is also counted.
    The output is a JSON to be rendered with this library
    https://github.com/benfred/venn.js
    Args:
        request ([type]): [description]
    """
    qs = DSSToxLookup.objects.annotate(
        grouptype=GroupConcat(
            "curated_chemical__extracted_text__data_document__data_group__group_type__id",
            distinct=True,
        )
    ).values_list("grouptype", flat=True)
    sets_cnt = {}

    def add_set(key):
        # Adds or creates set to sets_dict
        if key not in sets_cnt:
            sets_cnt[key] = 1
        else:
            sets_cnt[key] += 1

    # Count sets
    for group_str in qs:
        # Ignore "None"
        if group_str:
            # Each value is a concatenation of GroupType IDs separated by a comma.
            # Lets split them
            groups = group_str.split(",")
            # Then turn them into a list of integers
            groups = [int(i) for i in groups]
            # We want to make sure they are consistently sorted
            groups.sort()
            # We make them a tuple to use as a dictionary key
            groups = tuple(groups)
            # Record a count on it
            add_set(groups)
            # If this is more than one GroupType, we also want to count the GroupTypes
            # within the set
            if len(groups) > 1:
                for group in groups:
                    add_set((group,))

    # Here is a dictionary relating the GroupType ID we've counted on to its title
    titles = {
        g["id"]: g["title"]
        for g in GroupType.objects.all().order_by("id").values("id", "title")
    }
    # Create data
    sets = []
    for set_ids, set_cnt in sets_cnt.items():
        # List the titles, not IDs
        set_groups = [titles[i] for i in set_ids]
        # Make the final dictionary output
        sets.append({"sets": set_groups, "size": set_cnt})

    return JsonResponse({"data": sets})


class ProductPUCReconciliationJson(FilterDatatableView):
    """
    Provides JSON elements describing all Products where more 
    than one PUC has been assigned
    """

    model = ProductToPUC
    columns = [
        "product_id",
        "product__title",
        "puc",
        "classification_method",
        "classification_confidence",
    ]

    def render_column(self, row, column):
        value = self._render_column(row, column)
        if column == "product__title":
            return format_html(
                '<a href="{}" title="Go to Product detail" target="_blank">{}</a>',
                row.product.get_absolute_url(),
                row.product.title,
            )
        if column == "puc":
            return format_html(
                '<a href="{}" title="Go to PUC detail" target="_blank">{}</a>',
                row.puc.get_absolute_url(),
                value,
            )
        # if column == "unassign":
        #     return format_html(
        #         '<a href="unassign?puc={}&product={}" title="Remove assignment" target="_blank">Unassign</a>',
        #         row.puc_id,
        #         row.product_id,
        #     )
        return value

    def get_initial_queryset(self):
        dupes = (
            ProductToPUC.objects.values("product_id")
            .annotate(puc_count=Count("puc_id", distinct=True))
            .filter(puc_count__gte=2)
        )
        qs = ProductToPUC.objects.filter(
            product_id__in=Subquery(dupes.values("product_id"))
        ).order_by("product_id")
        return qs
