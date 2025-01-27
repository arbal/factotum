from urllib.parse import urlencode

from django.urls import reverse
from django.views import View
from django.views.generic.detail import SingleObjectMixin
from django_datatables_view.base_datatable_view import BaseDatatableView
from django.http import JsonResponse
from django.db.models import Q, Count, Subquery, Case, When, F, Value, OuterRef
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
    ExtractedCPCat,
    ExtractedListPresence,
    ExtractedListPresenceToTag,
    ExtractedListPresenceTag,
    FunctionalUseToRawChem,
    ExtractedHabitsAndPractices,
    RawChem,
    AuditLog,
    HarmonizedMedium,
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
        if column == "product_uber_puc.classification_method.name":
            if value:
                return format_html(
                    '<span title="{}">{}</span>',
                    row.product_uber_puc.classification_method.description,
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
    columns = ["title", "data_group.group_type.title", "extractedtext.doc_date"]

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

        if column == "extractedtext.doc_date":
            if hasattr(row, "extractedtext"):
                value = row.extractedtext.doc_date
            else:
                value = None
                return value
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
        if column == "data_group.group_type.title":
            return format_html(
                '<span title="{}">{}</span>',
                row.data_group.group_type.description,
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


class FUCProductListJson(FilterDatatableView):
    model = Product
    columns = [
        "title",
        "document.title",
        "product_uber_puc.puc",
        "product_uber_puc.classification_method.name",
    ]

    def render_column(self, row, column):
        value = self._render_column(row, column)
        if column == "title":
            return format_html(
                '<a href="{}" title="Go to Product detail" target="_blank">{}</a>',
                row.get_absolute_url(),
                value,
            )
        if column == "document.title":
            return format_html(
                '<a href="{}" title="Go to Data Document detail" target="_blank">{}</a>',
                row.document.get_absolute_url(),
                value,
            )
        if column == "product_uber_puc.puc":
            if value:
                return format_html(
                    '<a href="{}" title="Go to PUC detail" target="_blank">{}</a>',
                    row.product_uber_puc.puc.get_absolute_url(),
                    value,
                )
        if column == "product_uber_puc.classification_method.name":
            if value:
                return format_html(
                    '<span title="{}">{}</span>',
                    row.product_uber_puc.classification_method.description,
                    value,
                )
        return value

    def get_initial_queryset(self):
        qs = super().get_initial_queryset()
        fuc = self.request.GET.get("functional_use_category")
        qs = qs.select_related("product_uber_puc")
        if fuc:
            return qs.filter(
                Q(datadocument__extractedtext__rawchem__functional_uses__category=fuc)
            ).distinct()
        return qs


class FUCDocumentListJson(FilterDatatableView):
    model = RawChem
    columns = [
        "extracted_text__data_document__data_group__group_type__code",
        "extracted_text__data_document__title",
        "extracted_text__doc_date",
        "functional_uses__report_funcuse",
    ]

    def get_initial_queryset(self):
        qs = super().get_initial_queryset()
        fuc = self.request.GET.get("functional_use_category")
        if fuc:
            qs = qs.filter(Q(functional_uses__category=fuc))
        # using the .distinct() function means that a dict is returned, not
        # a queryset.
        qs = (
            qs.order_by(
                "extracted_text__data_document__data_group__group_type__code",
                "extracted_text__data_document__title",
            )
            .values(
                "extracted_text__data_document",
                "extracted_text__data_document__title",
                "extracted_text__data_document__data_group__group_type__code",
                "extracted_text__data_document__data_group__group_type__description",
                "extracted_text__doc_date",
                "functional_uses__report_funcuse",
            )
            .distinct()
        )
        return qs

    def render_column(self, row, column):
        value = self._render_column(row, column)
        if column == "extracted_text__data_document__title":
            doc_id = row["extracted_text__data_document"]
            doc = DataDocument.objects.get(pk=doc_id)
            return format_html(
                '<a href="{}" title="Go to Document detail" target="_blank">{}</a>',
                doc.get_absolute_url(),
                value,
            )
        if column == "extracted_text__data_document__data_group__group_type__code":
            return format_html(
                '<span title="{}">{}</span>',
                row[
                    "extracted_text__data_document__data_group__group_type__description"
                ],
                value,
            )
        return value


class FUCChemicalListJson(FilterDatatableView):
    model = DSSToxLookup
    columns = ["sid", "true_cas", "true_chemname"]

    def get_initial_queryset(self):
        qs = super().get_initial_queryset()
        fuc = self.request.GET.get("functional_use_category")
        if fuc:
            vals = (
                RawChem.objects.filter(dsstox__isnull=False)
                .filter(Q(functional_uses__category=fuc))
                .values("dsstox")
            )
            return qs.filter(pk__in=vals)
        return qs

    def render_column(self, row, column):
        value = self._render_column(row, column)
        if value and hasattr(row, "get_absolute_url"):
            if column == "true_chemname":
                return format_html(truncatechars(value, 89))
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


class HarmonizedMediumDocumentListJson(FilterDatatableView):
    model = DataDocument
    columns = [
        "data_group__group_type__code",
        "title",
        "extractedtext__doc_date",
        "extractedtext__rawchem__unionextractedlmhhrec__medium",
    ]

    def get_initial_queryset(self):
        qs = super().get_initial_queryset()
        medium = self.request.GET.get("medium")
        if medium:
            qs = qs.filter(
                Q(
                    extractedtext__rawchem__unionextractedlmhhrec__harmonized_medium=medium
                )
            )
        # using the .distinct() function means that a dict is returned, not
        # a queryset.
        qs = (
            qs.order_by("data_group__group_type__code", "title")
            .values(
                "id",
                "title",
                "data_group__group_type__code",
                "extractedtext__doc_date",
                "extractedtext__rawchem__unionextractedlmhhrec__medium",
            )
            .distinct()
        )
        return qs

    def render_column(self, row, column):
        value = self._render_column(row, column)
        if column == "title":
            doc_id = row["id"]
            doc = DataDocument.objects.get(pk=doc_id)
            return format_html(
                '<a href="{}" title="Go to Document detail" target="_blank">{}</a>',
                doc.get_absolute_url(),
                value,
            )
        return value


class HarmonizedMediumChemicalListJson(FilterDatatableView):
    model = DSSToxLookup
    columns = ["sid", "true_cas", "true_chemname"]

    def get_initial_queryset(self):
        qs = super().get_initial_queryset()
        medium = self.request.GET.get("medium")
        if medium:
            vals = (
                RawChem.objects.filter(dsstox__isnull=False)
                .filter(Q(unionextractedlmhhrec__harmonized_medium=medium))
                .values("dsstox")
            )
            return qs.filter(pk__in=vals)
        return qs

    def render_column(self, row, column):
        value = self._render_column(row, column)
        if value and hasattr(row, "get_absolute_url"):
            if column == "true_chemname":
                return format_html(truncatechars(value, 89))
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


class HabitsAndPracticesDocumentsJson(FilterDatatableView):
    model = ExtractedHabitsAndPractices
    columns = [
        "extracted_text.data_document.title",
        "product_surveyed",
        "data_type.title",
    ]

    def get_initial_queryset(self):
        qs = super().get_initial_queryset()
        puc = self.request.GET.get("puc")
        if puc:
            return qs.filter(Q(puc=puc))
        return qs

    def render_column(self, row, column):
        value = self._render_column(row, column)
        if column == "extracted_text.data_document.title":
            return format_html(
                '<a href="{}" title="Go to Document detail" target="_blank">{}</a>',
                row.extracted_text.data_document.get_absolute_url()
                + "#chem-card-"
                + str(row.pk),
                value,
            )
        return value


class CuratedChemicalsListJson(FilterDatatableView):
    model = RawChem
    columns = [
        "dsstox__sid",
        "raw_chem_name",
        "raw_cas",
        "dsstox__true_chemname",
        "dsstox__true_cas",
        "count",
    ]

    def get_initial_queryset(self):
        qs = super().get_initial_queryset().filter(dsstox__isnull=False)
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(Q(raw_chem_name__icontains=q) | Q(raw_cas__icontains=q))
        qs = qs.values(
            "dsstox__sid",
            "raw_chem_name",
            "raw_cas",
            "dsstox__true_chemname",
            "dsstox__true_cas",
        ).annotate(count=Count("id"))
        return qs

    def render_column(self, row, column):
        if column == "count":
            detail_url = reverse(
                "curated_chemical_detail", kwargs={"sid": row["dsstox__sid"]}
            )
            params = {
                "raw_chem_name": row["raw_chem_name"],
                "raw_cas": row["raw_cas"],
                "dsstox__true_chemname": row["dsstox__true_chemname"],
                "dsstox__true_cas": row["dsstox__true_cas"],
            }
            detail_url += "?" + urlencode(params)
            return f"<a href='{detail_url}' target='_blank'>{row['count']}</a>"
        return super().render_column(row, column)


class CuratedChemicalDetailJson(FilterDatatableView):
    model = RawChem
    columns = ["extracted_text.data_document.title", "sid_updated", "provisional"]

    def get_initial_queryset(self):
        sid = self.request.GET.get("sid")
        raw_chem_name = self.request.GET.get("raw_chem_name")
        raw_cas = self.request.GET.get("raw_cas")

        sid_log = (
            AuditLog.objects.filter(rawchem_id=OuterRef("pk"), field_name="sid")
            .order_by("-date_created")
            .values("date_created")
        )

        qs = (
            super()
            .get_initial_queryset()
            .prefetch_related("extracted_text__data_document", "dsstox")
            .filter(dsstox__sid=sid, raw_chem_name=raw_chem_name, raw_cas=raw_cas)
            .annotate(sid_updated=Subquery(sid_log[:1]))
        )
        return qs

    def render_column(self, row, column):
        if column == "extracted_text.data_document.title":
            dd_url = reverse(
                "data_document", args=[row.extracted_text.data_document.id]
            )
            dd_url += f"#chem-card-{row.id}"
            return f"<a href='{dd_url}' target='_blank'>{row.extracted_text.data_document.title}</a>"
        elif column == "sid_updated":
            return (
                row.sid_updated.strftime("%b %d, %Y, %I:%M:%S %p")
                if row.sid_updated
                else ""
            )
        elif column == "provisional":
            return "Yes" if row.provisional else "No"
        return super().render_column(row, column)

    def filter_queryset(self, qs):
        pv = self.request.GET.get("provisional")
        if pv and pv != "all":
            qs = qs.filter(provisional=pv)
        return super().filter_queryset(qs)
