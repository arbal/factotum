from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, reverse, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, F
from dashboard.models import FunctionalUse, FunctionalUseCategory
from django.http import JsonResponse
import json
from django.db.models import Count, F, Exists, Case, When, Q, Value
from django.views.generic import TemplateView
from django_datatables_view.base_datatable_view import BaseDatatableView

from dashboard.models import FunctionalUse, RawChem


@login_required()
def functional_use_curation(request):
    template_name = "functional_use_curation/functional_use_curation.html"

    combinations = (
        FunctionalUse.objects.values("pk", "report_funcuse", "category__title")
        .annotate(fu_count=Count("chemicals"))
    if request.method == "POST":
        cat = json.loads(request.POST.get("json") or "{}")
        FunctionalUse.objects.filter(report_funcuse=cat["report_funcuse"], category=cat["category"]).update(category=cat["newcategory"])
        print(cat)

        response_data = {}

        return JsonResponse(response_data)

    combinations = FunctionalUse.objects.values("report_funcuse", "category", newcategory=F("category"),
                                                categorytitle=F("category__title")) \
        .annotate(fu_count=Count("id")) \
        .order_by("report_funcuse", "category__title")

    categories = FunctionalUseCategory.objects.values("id", "title").order_by("title")
    categorylist = [{'id': '', 'title': ''}] + list(categories)

    return render(request, template_name, {"combinations": list(combinations), "categories": categorylist})


class FunctionalUseCurationChemicals(LoginRequiredMixin, TemplateView):
    template_name = "functional_use_curation/functional_use_curation_chemicals.html"
    table_settings = {"pagination": True, "pageLength": 50}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["functional_use"] = get_object_or_404(
            FunctionalUse, pk=self.kwargs.get("functional_use_pk")
        )
        self.table_settings["ajax"] = reverse(
            "functional_use_curation_chemicals_table", kwargs=self.kwargs
        )
        context["table_settings"] = self.table_settings

        return context


class FunctionalUseCurationChemicalsTable(BaseDatatableView):
    model = RawChem

    def get_filter_method(self):
        """ Returns preferred filter method """
        return self.FILTER_ICONTAINS

    def render_column(self, row, column):
        if column == "preferred_name":
            return f"""
                <a href='{row.extracted_text.data_document.get_absolute_url()}'>
                  {row.preferred_name}
                </a>"""
        if column == "functional_uses":
            return ", ".join(
                row.functional_uses.values_list("report_funcuse", flat=True)
            )
        if column == "extracted_text__data_document__title":
            return row.extracted_text.data_document.title
        return super().render_column(row, column)

    def get_initial_queryset(self):
        functional_use = get_object_or_404(
            FunctionalUse, pk=self.kwargs.get("functional_use_pk")
        )
        qs = super().get_initial_queryset()
        qs = (
            qs.filter(functional_uses=functional_use)
            .annotate(
                preferred_name=Case(
                    # no dsstox
                    When(dsstox__isnull=False, then=F("dsstox__true_chemname")),
                    # not blank raw_chem_name
                    When(~Q(raw_chem_name=""), then=F("raw_chem_name")),
                    # no true chem no raw_chem_name
                    default=Value("Unnamed Chemical"),
                )
            )
            .order_by("pk")
        )
        return qs
