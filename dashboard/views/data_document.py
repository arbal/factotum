from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponseBadRequest
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views import View
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.shortcuts import render, redirect, get_object_or_404, reverse
from django_datatables_view.base_datatable_view import BaseDatatableView
from djqscsv import render_to_csv_response

from dashboard.forms.forms import (
    ExtractedHabitsAndPracticesForm,
    RawChemToFunctionalUseForm,
)
from dashboard.forms.tag_forms import ExtractedHabitsAndPracticesTagForm
from dashboard.utils import get_extracted_models, GroupConcat
from dashboard.forms import (
    ExtractedListPresenceTagForm,
    create_detail_formset,
    DataDocumentForm,
    DocumentTypeForm,
    ExtractedCompositionForm,
    ExtractedLMChemicalForm,
    ExtractedFunctionalUseForm,
    ExtractedHHRecForm,
    ExtractedListPresenceForm,
)
from dashboard.models import (
    DataDocument,
    ExtractedListPresence,
    ExtractedText,
    FunctionalUse,
    Script,
    ExtractedListPresenceToTag,
    ExtractedListPresenceTag,
    ExtractedComposition,
    RawChem,
    AuditLog,
    ExtractedHabitsAndPractices,
    ExtractedHabitsAndPracticesToTag,
    ExtractedFunctionalUse,
    DataGroup,
    FunctionalUseToRawChem,
)
from django.forms import inlineformset_factory
from django import forms

CHEMICAL_FORMS = {
    "CO": ExtractedCompositionForm,
    "LM": ExtractedLMChemicalForm,
    "FU": ExtractedFunctionalUseForm,
    "CP": ExtractedListPresenceForm,
    "HP": ExtractedHabitsAndPracticesForm,
    "HH": ExtractedHHRecForm,
}
CHEMICAL_TYPES = CHEMICAL_FORMS.keys()


def data_document_detail(request, pk):
    template_name = "data_document/data_document_detail.html"
    doc = get_object_or_404(DataDocument, pk=pk)
    if doc.data_group.group_type.code == "SD":
        messages.info(
            request,
            f'"{doc}" has no detail page. GroupType is "{doc.data_group.group_type}"',
        )
        return redirect(reverse("data_group_detail", args=[doc.data_group_id]))
    ParentForm, _ = create_detail_formset(doc)
    Parent, Child = get_extracted_models(doc.data_group.group_type.code)
    ext = Parent.objects.filter(pk=doc.pk).first()
    fufs = []
    tag_form = None

    if doc.data_group.group_type.code in CHEMICAL_TYPES:
        if Child == ExtractedListPresence:
            tag_form = ExtractedListPresenceTagForm()

        if Child == ExtractedHabitsAndPractices:
            tag_form = ExtractedHabitsAndPracticesTagForm()

        else:
            chem = (
                Child.objects.filter(extracted_text__data_document=doc)
                .prefetch_related("dsstox")
                .first()
            )
            FuncUseFormSet = inlineformset_factory(
                RawChem,
                RawChem.functional_uses.through,
                form=RawChemToFunctionalUseForm,
                extra=1,
            )
            fufs = FuncUseFormSet(instance=chem)
    context = {
        "fufs": fufs,
        "doc": doc,
        "extracted_text": ext,
        "edit_text_form": ParentForm(instance=ext),  # empty form if ext is None
        "tag_form": tag_form,
    }
    if doc.data_group.group_type.code == "CO":
        script_chem = (
            Child.objects.filter(extracted_text__data_document=doc)
            .filter(script__isnull=False)
            .first()
        )
        context["cleaning_script"] = script_chem.script if script_chem else None

    tags = (
        ExtractedListPresenceTag.objects.filter(
            extractedlistpresence__extracted_text__data_document=doc
        )
        .values_list("id", "name", named=True)
        .distinct()
    )
    context["tags"] = tags
    return render(request, template_name, context)


@method_decorator(login_required, name="dispatch")
class ChemCreateView(CreateView):
    template_name = "chemicals/chemical_add_form.html"

    def get_form_kwargs(self):
        kwargs = super(ChemCreateView, self).get_form_kwargs()
        if self.request.headers.get("Referer", None):
            kwargs.update({"referer": self.request.headers.get("Referer")})
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        doc = DataDocument.objects.get(pk=self.kwargs.get("doc"))
        extra = (
            12
            if doc.data_group.can_have_multiple_funcuse
            else 1
            if doc.data_group.can_have_funcuse
            else 0
        )
        FuncUseFormSet = inlineformset_factory(
            RawChem,
            RawChem.functional_uses.through,
            form=RawChemToFunctionalUseForm,
            extra=extra,
            can_delete=False,
        )
        context.update(
            {"formset": FuncUseFormSet, "doc": doc, "post_url": "chemical_create"}
        )
        if not "fufs" in context:
            context["fufs"] = FuncUseFormSet()
        return context

    def get_form_class(self):
        doc = DataDocument.objects.get(pk=self.kwargs.get("doc"))
        code = doc.data_group.group_type.code
        return CHEMICAL_FORMS[code]

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))

    def form_valid(self, form):
        form.instance.extracted_text_id = self.kwargs.get("doc")
        self.object = form.save()
        FuncUseFormSet = self.get_context_data()["formset"]
        formset = FuncUseFormSet(self.request.POST, instance=self.object)
        if formset.is_valid():
            formset.save()
            return render(
                self.request,
                "chemicals/chemical_create_success.html",
                {"chemical": self.object},
            )
        else:
            return self.form_invalid(form)


@method_decorator(login_required, name="dispatch")
class ChemUpdateView(UpdateView):
    template_name = "chemicals/chemical_edit_form.html"
    model = RawChem

    def get_object(self, queryset=None):
        obj = super(ChemUpdateView, self).get_object(queryset=queryset)
        return RawChem.objects.get_subclass(pk=obj.pk)

    def get_form_kwargs(self):
        kwargs = super(ChemUpdateView, self).get_form_kwargs()
        if self.request.headers.get("Referer", None):
            kwargs.update({"referer": self.request.headers.get("Referer")})
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        doc = self.object.extracted_text.data_document
        extra = (
            12
            if doc.data_group.can_have_multiple_funcuse
            else 1
            if doc.data_group.can_have_funcuse
            else 0
        )
        FuncUseFormSet = inlineformset_factory(
            RawChem,
            RawChem.functional_uses.through,
            form=RawChemToFunctionalUseForm,
            extra=extra,
            can_delete=True,
        )
        context.update(
            {"formset": FuncUseFormSet, "doc": doc, "post_url": "chemical_update"}
        )
        if not "fufs" in context:
            context["fufs"] = FuncUseFormSet(instance=self.object)
        return context

    def get_form_class(self):
        code = self.object.extracted_text.group_type
        return CHEMICAL_FORMS[code]

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))

    def form_valid(self, form):
        self.object = form.save()
        FuncUseFormSet = self.get_context_data()["formset"]
        formset = FuncUseFormSet(self.request.POST, instance=self.object)
        if formset.is_valid():
            formset.save()
            return render(
                self.request,
                "chemicals/chemical_create_success.html",
                {"chemical": self.object},
            )
        else:
            return self.form_invalid(form)


@method_decorator(login_required, name="dispatch")
class EHPCreateView(CreateView):
    template_name = "chemicals/chemical_add_form.html"
    model = DataDocument
    form_class = ExtractedHabitsAndPracticesForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        doc = DataDocument.objects.get(pk=self.kwargs.get("doc"))
        context.update({"post_url": "ehp_create", "doc": doc})
        return context

    def form_valid(self, form):
        form.instance.extracted_text_id = self.kwargs.get("doc")
        extracted_habits_and_practices = form.save()
        return render(
            self.request,
            "chemicals/chemical_create_success.html",
            {"chemical": extracted_habits_and_practices},
        )


@method_decorator(login_required, name="dispatch")
class EHPUpdateView(UpdateView):
    template_name = "chemicals/chemical_edit_form.html"
    model = ExtractedHabitsAndPractices
    form_class = ExtractedHabitsAndPracticesForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"post_url": "ehp_update"})
        return context

    def form_valid(self, form):
        self.object = form.save()
        return render(
            self.request,
            "chemicals/chemical_create_success.html",
            {"chemical": self.object},
        )


@method_decorator(login_required, name="dispatch")
class EHPDeleteView(DeleteView):
    model = ExtractedHabitsAndPractices

    def get_success_url(self):
        return reverse("data_document", args=[self.kwargs.get("doc")])


@login_required()
def save_data_document_type(request, pk):
    """Writes changes to the data document type form

    The request object should have a 'referer' key to redirect the
    browser to the appropriate place after saving the edits

    Invoked by changing the document type in the data document detail view or the
    extracted text QA page template
    """

    referer = request.POST.get("referer", "data_document")
    doc = get_object_or_404(DataDocument, pk=pk)
    document_type_form = DocumentTypeForm(request.POST, instance=doc)
    if document_type_form.is_valid() and document_type_form.has_changed():
        document_type_form.save()
    return redirect(referer, pk=pk)


@login_required()
def save_data_document_note(request, pk):
    doc = get_object_or_404(DataDocument, pk=pk)
    doc_note = request.POST["dd_note"]
    doc.note = doc_note
    doc.save()
    return redirect("data_document", pk=pk)


@login_required()
def save_data_document_extext(request, pk):
    referer = request.POST.get("referer", "data_document")
    doc = get_object_or_404(DataDocument, pk=pk)
    ExtractedTextForm, _ = create_detail_formset(doc)
    extracted_text = ExtractedText.objects.get_subclass(pk=pk)
    ext_text_form = ExtractedTextForm(request.POST, instance=extracted_text)
    if ext_text_form.is_valid() and ext_text_form.has_changed():
        ext_text_form.save()
    return redirect(referer, pk=pk)


@method_decorator(login_required, name="dispatch")
class SaveTagForm(View):
    http_method_names = ["post"]
    pk = None
    group_type_code = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.pk = kwargs.get("pk")
        extracted_text = get_object_or_404(ExtractedText, pk=self.pk)
        self.group_type_code = extracted_text.data_document.data_group.group_type.code

    def post(self, *args, **kwargs):
        referer = self.request.POST.get("referer", "data_document")

        if self.group_type_code == "CP":
            tag_form_class = ExtractedListPresenceTagForm
        elif self.group_type_code == "HP":
            tag_form_class = ExtractedHabitsAndPracticesTagForm
        else:
            messages.error(self.request, "This Group Type does not support tagging")
            return redirect(referer, pk=self.pk)

        tag_form = tag_form_class(self.request.POST)
        if tag_form.is_valid():
            tag_form.save()
        else:
            messages.error(self.request, tag_form.errors)

        if not tag_form.errors:
            tag_string_list = list(
                map(lambda x: str(x), tag_form.cleaned_data.get("tags"))
            )
            chem_string_list = list(
                map(
                    lambda x: str(x) if str(x) else "None",
                    tag_form.cleaned_data.get("chems"),
                )
            )

            messages.success(
                self.request,
                f"Tags [{', '.join(tag_string_list)}]"
                " are now connected to "
                f"[{self._list_to_truncated_string(chem_string_list, 10)}]",
            )
        return redirect(referer, pk=self.pk)

    def _list_to_truncated_string(self, string_list, truncation_number):
        if len(string_list) <= truncation_number:
            return ", ".join(string_list)

        base_string = ", ".join(string_list[:truncation_number])
        trunc_string = f" ({str(len(string_list) - truncation_number)} results hidden)"

        return base_string + trunc_string


@login_required()
def data_document_delete(request, pk):
    doc = get_object_or_404(DataDocument, pk=pk)
    datagroup_id = doc.data_group_id
    if request.method == "POST":
        doc.delete()
        return redirect("data_group_detail", pk=datagroup_id)
    return render(
        request, "data_source/datasource_confirm_delete.html", {"object": doc}
    )


@login_required
def data_document_edit(request, pk):
    datadocument = get_object_or_404(DataDocument, pk=pk)
    form = DataDocumentForm(request.POST or None, instance=datadocument)
    form.referer = (
        request.POST.get("referer_page")
        if request.POST.get("referer_page")
        else request.META.get("HTTP_REFERER", None)
    )
    if form.is_valid():
        if form.has_changed():
            form.save()
        if form.referer:
            return redirect(form.referer)
        return redirect("data_document", pk=pk)

    return render(request, "data_document/data_document_form.html", {"form": form})


@login_required()
def data_document_create(request, pk):
    data_group = get_object_or_404(DataGroup, pk=pk)
    form = DataDocumentForm(
        request.POST or None,
        request.FILES or None,
        user=request.user,
        data_group=data_group,
        initial={"downloaded_by": request.user},
    )
    form.referer = (
        request.POST.get("referer_page")
        if request.POST.get("referer_page")
        else request.META.get("HTTP_REFERER", None)
    )
    if form.is_valid():
        form.save()
        if form.referer:
            return redirect(form.referer)
        return redirect("data_document", pk=pk)
    return render(
        request,
        "data_document/data_document_create_form.html",
        {"form": form, "data_group": data_group},
    )


@login_required
def extracted_text_edit(request, pk):
    doc = get_object_or_404(DataDocument, pk=pk)
    ParentForm, _ = create_detail_formset(doc, extra=0, can_delete=False)
    model = ParentForm.Meta.model
    script = Script.objects.get(title__icontains="Manual (dummy)", script_type="EX")
    try:
        extracted_text = model.objects.get_subclass(data_document_id=pk)
    except ExtractedText.DoesNotExist:
        extracted_text = model(data_document_id=pk, extraction_script=script)
    form = ParentForm(request.POST, instance=extracted_text)
    if form.is_valid():
        form.save()
        doc.save()
        return JsonResponse({"message": "success"})
    return JsonResponse(form.errors, status=400)


@login_required
def list_presence_tag_curation(request):
    documents = (
        DataDocument.objects.filter(
            data_group__group_type__code="CP", extractedtext__rawchem__isnull=False
        )
        .distinct()
        .exclude(
            extractedtext__rawchem__in=ExtractedListPresenceToTag.objects.values(
                "content_object_id"
            )
        )
    )
    return render(
        request, "data_document/list_presence_tag.html", {"documents": documents}
    )


@login_required()
def data_document_delete_tags(request, pk):
    doc = get_object_or_404(DataDocument, pk=pk)

    if doc.data_group.is_chemical_presence:
        ExtractedListPresenceToTag.objects.filter(
            content_object__extracted_text__data_document_id=pk
        ).delete()

    if doc.data_group.is_habits_and_practices:
        ExtractedHabitsAndPracticesToTag.objects.filter(
            content_object__extracted_text__data_document_id=pk
        ).delete()

    url = reverse("data_document", args=[pk])
    return redirect(url)


@login_required
def list_presence_tag_delete(request, doc_pk, chem_pk, tag_pk):
    elp = ExtractedListPresence.objects.get(pk=chem_pk)
    tag = ExtractedListPresenceTag.objects.get(pk=tag_pk)
    ExtractedListPresenceToTag.objects.get(content_object=elp, tag=tag).delete()
    card = f"#chem-card-{chem_pk}"
    url = reverse("data_document", args=[doc_pk])
    url += card
    return redirect(url)


@login_required
def detected_flag(request, doc_pk):
    chems = request.POST.getlist("chems")
    flag_set = int
    if "non_detected" in request.get_full_path():
        flag_set = 0
    elif "detected" in request.get_full_path():
        flag_set = 1
    elif "clear_flag" in request.get_full_path():
        flag_set = None
    else:
        pass

    for chem in chems:
        elp = RawChem.objects.get(pk=chem)
        elp.chem_detected_flag = flag_set
        elp.save()
    url = reverse("data_document", args=[doc_pk])
    return redirect(url)


@login_required
def habits_and_practices_tag_delete(request, doc_pk, chem_pk, tag_pk):
    ExtractedHabitsAndPracticesToTag.objects.filter(
        content_object_id=chem_pk, tag_id=tag_pk
    ).delete()
    card = f"#chem-card-{chem_pk}"
    url = reverse("data_document", args=[doc_pk])
    url += card
    return redirect(url)


def chemical_audit_log(request, pk):
    chemical = RawChem.objects.filter(pk=pk).select_subclasses().first()
    auditlog = AuditLog.objects.filter(rawchem_id=pk).order_by("-date_created")

    return render(
        request,
        "chemicals/chemical_audit_log.html",
        {"chemical": chemical, "auditlog": auditlog},
    )


def download_document_chemicals(request, pk):
    def download_list_presence_chemicals():
        chemicals = (
            ExtractedListPresence.objects.filter(
                extracted_text__data_document_id=document.pk
            )
            .annotate(
                tag_names=GroupConcat("tags__name", separator="; ", distinct=True)
            )
            .values(
                "extracted_text__data_document__title",
                "extracted_text__data_document__subtitle",
                "extracted_text__data_document__organization",
                "raw_chem_name",
                "raw_cas",
                "dsstox__sid",
                "dsstox__true_chemname",
                "dsstox__true_cas",
                "tag_names",
                "provisional",
                "functional_uses__report_funcuse",
                "functional_uses__category__title",
            )
            .order_by("raw_chem_name")
        )
        filename = document.get_title_as_slug() + "_chemicals.csv"
        return render_to_csv_response(
            chemicals,
            filename=filename,
            append_datestamp=True,
            field_header_map={
                "extracted_text__data_document__title": "Data Document Title",
                "extracted_text__data_document__subtitle": "Data Document Subtitle",
                "extracted_text__data_document__organization": "Organization",
                "dsstox__sid": "DTXSID",
                "dsstox__true_chemname": "True Chemical Name",
                "dsstox__true_cas": "True CAS",
                "tag_names": "Tags",
                "provisional": "Provisional",
                "functional_uses__report_funcuse": "Reported Functional Use",
                "functional_uses__category__title": "Harmonized Functional Use",
            },
            field_serializer_map={
                "provisional": (lambda f: ("Yes" if f == "1" else "No"))
            },
        )

    def download_composition_chemicals():
        chemicals = (
            ExtractedComposition.objects.filter(
                extracted_text__data_document_id=document.pk
            )
            .prefetch_related("weight_fraction_type", "unit_type")
            .values(
                "extracted_text__data_document__title",
                "extracted_text__data_document__subtitle",
                "extracted_text__data_document__organization",
                "raw_chem_name",
                "raw_cas",
                "dsstox__sid",
                "dsstox__true_chemname",
                "dsstox__true_cas",
                "ingredient_rank",
                "has_composition_data",
                "raw_min_comp",
                "raw_max_comp",
                "raw_central_comp",
                "unit_type__title",
                "lower_wf_analysis",
                "upper_wf_analysis",
                "central_wf_analysis",
                "weight_fraction_type__title",
                "component",
                "provisional",
                "functional_uses__report_funcuse",
                "functional_uses__category__title",
            )
            .order_by("raw_chem_name")
        )
        filename = document.get_title_as_slug() + "_chemicals.csv"
        return render_to_csv_response(
            chemicals,
            filename=filename,
            append_datestamp=True,
            field_header_map={
                "extracted_text__data_document__title": "Data Document Title",
                "extracted_text__data_document__subtitle": "Data Document Subtitle",
                "extracted_text__data_document__organization": "Organization",
                "dsstox__sid": "DTXSID",
                "dsstox__true_chemname": "True Chemical Name",
                "dsstox__true_cas": "True CAS",
                "ingredient_rank": "Ingredient Rank",
                "has_composition_data": "Has Composition Data",
                "raw_min_comp": "Raw Min Comp",
                "raw_max_comp": "Raw Max Comp",
                "raw_central_comp": "Raw Central Comp",
                "unit_type__title": "Unit Type",
                "lower_wf_analysis": "Lower Weight Fraction",
                "upper_wf_analysis": "Upper Weight Fraction",
                "central_wf_analysis": "Central Weight Fraction",
                "weight_fraction_type__title": "Weight Fraction Type",
                "provisional": "Provisional",
                "functional_uses__report_funcuse": "Reported Functional Use",
                "functional_uses__category__title": "Harmonized Functional Use",
            },
            field_serializer_map={
                "provisional": (lambda f: ("Yes" if f == "1" else "No"))
            },
        )

    def download_functional_use_chemicals():
        chemicals = (
            ExtractedFunctionalUse.objects.filter(
                extracted_text__data_document_id=document.pk
            )
            .values(
                "extracted_text__data_document__title",
                "extracted_text__data_document__subtitle",
                "extracted_text__data_document__organization",
                "raw_chem_name",
                "raw_cas",
                "dsstox__sid",
                "dsstox__true_chemname",
                "dsstox__true_cas",
                "provisional",
                "functional_uses__report_funcuse",
                "functional_uses__category__title",
            )
            .order_by("raw_chem_name")
        )
        filename = document.get_title_as_slug() + "_chemicals.csv"
        return render_to_csv_response(
            chemicals,
            filename=filename,
            append_datestamp=True,
            field_header_map={
                "extracted_text__data_document__title": "Data Document Title",
                "extracted_text__data_document__subtitle": "Data Document Subtitle",
                "extracted_text__data_document__organization": "Organization",
                "dsstox__sid": "DTXSID",
                "dsstox__true_chemname": "True Chemical Name",
                "dsstox__true_cas": "True CAS",
                "provisional": "Provisional",
                "functional_uses__report_funcuse": "Reported Functional Use",
                "functional_uses__category__title": "Harmonized Functional Use",
            },
            field_serializer_map={
                "provisional": (lambda f: ("Yes" if f == "1" else "No"))
            },
        )

    document = get_object_or_404(DataDocument, pk=pk)
    if document.data_group.is_chemical_presence:
        return download_list_presence_chemicals()
    elif document.data_group.is_composition:
        return download_composition_chemicals()
    elif document.data_group.is_functional_use:
        return download_functional_use_chemicals()
    else:
        return HttpResponseBadRequest(
            content="data document does not belong to chemical presence or composition or functional use group",
            content_type="text/plain;",
        )


class DocumentAuditLog(BaseDatatableView):
    model = AuditLog
    columns = ["date_created", "field_name", "old_value", "new_value", "action", "user"]
    none_string = None

    def get(self, request, pk, *args, **kwargs):
        self.pk = pk
        return super().get(request, *args, **kwargs)

    def get_initial_queryset(self):
        qs = (
            self.model.objects.filter(extracted_text_id=self.pk)
            .order_by("-date_created")
            .all()
        )

        return qs


def document_audit_log(request, pk):
    return render(
        request,
        "data_document/document_audit_log.html",
        {"table_url": reverse("document_audit_log_table", args=[pk])},
    )


def data_document_cards(request, pk):
    """
    The template used to render the collection of cards depends on the type of
    data document being displayed. The `get_extracted_models` method in
    `dashboard/utils.py` returns the model class of the parent and child records,
    while this method chooses the appropriate html template.
    """
    doc = get_object_or_404(DataDocument, pk=pk)
    _, Child = get_extracted_models(doc.data_group.group_type.code)
    card_qs = Child.objects.filter(extracted_text__data_document=doc)

    return cards_detail(request, doc, card_qs, True)


def cards_detail(request, doc, card_qs, paginate=False):
    _, Child = get_extracted_models(doc.data_group.group_type.code)

    if Child == ExtractedListPresence:
        card_qs = card_qs.prefetch_related("tags", "dsstox").order_by("raw_chem_name")
        template = "data_document/cards/co_cp_cards.html"

    elif Child == ExtractedComposition:
        card_qs = card_qs.order_by("component", "ingredient_rank").prefetch_related(
            "dsstox"
        )
        template = "data_document/cards/co_cp_cards.html"

    elif Child == ExtractedHabitsAndPractices:
        card_qs = card_qs.prefetch_related("tags").order_by("product_surveyed")
        template = "data_document/cards/hp_cards.html"

    elif Child == ExtractedFunctionalUse:
        card_qs = card_qs.order_by("raw_chem_name")
        template = "data_document/cards/functional_use_cards.html"

    else:
        card_qs = card_qs.prefetch_related("dsstox").order_by("raw_chem_name")
        template = "data_document/cards/cards.html"

    if paginate:
        paginator = Paginator(card_qs, 500)
        page = request.GET.get("page")
        page = 1 if page is None else page
        card_qs_page = paginator.page(page)
    else:
        card_qs_page = card_qs

    return render(request, template, {"doc": doc, "chemicals": card_qs_page})
