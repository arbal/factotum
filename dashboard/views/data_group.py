import csv
import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Exists, F, OuterRef, Value, Case, When
from django.db.models.functions import Concat
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.defaultfilters import pluralize, register
from djqscsv import render_to_csv_response
from celery import shared_task
from celery_usertask.tasks import UserTask, usertask
from django.db import transaction
from django.db.models import Count

from dashboard.forms import DataGroupForm, create_detail_formset
from dashboard.forms.data_group import (
    BulkAssignProdForm,
    CleanCompFormSet,
    ExtractFileFormSet,
    UploadDocsForm,
    RegisterRecordsFormSet,
    ProductBulkCSVFormSet,
)
from dashboard.forms.forms import DataGroupWorkflowForm
from dashboard.models import (
    ExtractedText,
    Script,
    ExtractedComposition,
    DataSource,
    DocumentType,
    GroupType,
    DataDocument,
    DataGroup,
    FunctionalUse,
    DataGroupCurationWorkflow,
    CurationStep,
)
from dashboard.utils import gather_errors, zip_stream
from factotum.environment import env


@login_required()
def data_group_list(request, code=None, template_name="data_group/datagroup_list.html"):
    if code:
        group = get_object_or_404(GroupType, code=code)
        datagroups = (
            DataGroup.objects.filter(group_type=group)
            .values(
                "group_type__title",
                "name",
                "data_source",
                "data_source__title",
                "id",
                "downloaded_by__username",
                "downloaded_at",
                "download_script",
                "download_script__url",
                "download_script__title",
            )
            .annotate(num_extracted=Count("datadocument__extractedtext"))
            .order_by("name")
        )
    else:
        datagroups = (
            DataGroup.objects.all()
            .values(
                "group_type__title",
                "name",
                "data_source",
                "data_source__title",
                "id",
                "downloaded_by__username",
                "downloaded_at",
                "download_script",
                "download_script__url",
                "download_script__title",
            )
            .annotate(num_extracted=Count("datadocument__extractedtext"))
            .order_by("name")
        )
    data = {}
    data["datagroups"] = list(datagroups)
    return render(request, template_name, data)


@login_required()
def data_group_detail(request, pk, template_name="data_group/datagroup_detail.html"):
    dg = get_object_or_404(DataGroup, pk=pk)
    tabledata = {
        "boolComp": dg.is_composition,
        "boolHab": dg.is_habits_and_practices,
        "boolSD": dg.is_supplemental_doc,
        "numregistered": dg.registered_docs(),
        "nummatched": dg.matched_docs(),
        "numextracted": dg.extracted_docs(),
    }
    context = {
        "datagroup": dg,
        "hasproducts": dg.get_products().count() > 0,
        "tabledata": tabledata,
        "clean_comp_data_fieldnames": ", ".join(
            [
                "ExtractedComposition_id" if x == "id" else x
                for x in dg.get_clean_comp_data_fieldnames()
            ]
        ),
        "product_data_fieldnames": ", ".join(
            [
                "ExtractedComposition_id" if x == "id" else x
                for x in dg.get_product_template_fieldnames()
            ]
        ),
        "uploaddocs_form": None,
        "extfile_formset": None,
        "cleancomp_formset": None,
        "bulkassignprod_form": None,
        "product_formset": None,
        "functional_use_formset": None,
        "env": {
            "PRODUCT_IMAGE_DIRECTORY_MAX_UPLOAD": env.PRODUCT_IMAGE_DIRECTORY_MAX_UPLOAD,
            "PRODUCT_IMAGE_DIRECTORY_MAX_FILE_COUNT": env.PRODUCT_IMAGE_DIRECTORY_MAX_FILE_COUNT,
            "PRODUCT_IMAGE_MAX_SIZE": env.PRODUCT_IMAGE_MAX_SIZE,
        },
    }
    # TODO: Lots of boilerplate code here.
    if dg.include_upload_docs_form():
        if "uploaddocs-submit" in request.POST:
            form = UploadDocsForm(dg, request.POST, request.FILES)
            context["uploaddocs_form"] = UploadDocsForm(dg, request.POST, request.FILES)
            if form.is_valid():
                num_saved = form.save()
                messages.success(
                    request,
                    "%d document%s uploaded successfully."
                    % (num_saved, pluralize(num_saved)),
                )
            else:
                errors = gather_errors(form)
                for e in errors:
                    messages.error(request, e)
            return redirect("data_group_detail", dg.pk)
        context["uploaddocs_form"] = UploadDocsForm(dg)

    if dg.include_extract_form():
        if "extfile-submit" in request.POST:
            formset = ExtractFileFormSet(request.POST, request.FILES, dgpk=dg.pk)
            async_result = formset.enqueue(f"extfile_formset.{dg.pk}")
            return HttpResponseRedirect(
                reverse("data_group_detail", args=[dg.pk])
                + f"?task_id={async_result.id}"
            )
        context["extfile_formset"] = ExtractFileFormSet(dgpk=dg.pk)

    if dg.include_clean_comp_data_form():
        if "cleancomp-submit" in request.POST:
            formset = CleanCompFormSet(dg, request.POST, request.FILES)
            context["cleancomp_formset"] = CleanCompFormSet(dg, request.POST)
            if formset.is_valid():
                num_saved = formset.save()
                # save the cleaning script id to the extracted text records
                cleaning_script_id = request.POST["cleancomp-cleaning_script_id"]

                messages.success(
                    request,
                    "%d clean composition data record%s uploaded successfully."
                    % (num_saved, pluralize(num_saved)),
                )
            else:
                errors = gather_errors(formset)
                for e in errors:
                    messages.error(request, e)
            return redirect("data_group_detail", dg.pk)
        context["cleancomp_formset"] = CleanCompFormSet(dg)

    if dg.include_bulk_assign_form():
        if "bulkassignprod-submit" in request.POST:
            form = BulkAssignProdForm(dg, request.POST, request.FILES)
            if form.is_valid():
                num_saved = form.save()
                messages.success(
                    request,
                    "%d product%s created successfully."
                    % (num_saved, pluralize(num_saved)),
                )
            else:
                errors = gather_errors(form)
                for e in errors:
                    messages.error(request, e)
            return redirect("data_group_detail", dg.pk)
        context["bulkassignprod_form"] = BulkAssignProdForm(dg)

    if dg.include_product_upload_form():
        if "products-submit" in request.POST:
            product_formset = ProductBulkCSVFormSet(request.POST, request.FILES)
            if product_formset.is_valid():
                num_saved, reports = product_formset.save()
                messages.success(
                    request, f"{num_saved} records have been successfully uploaded."
                )
                for report in reports:
                    messages.warning(request, report)
            else:
                errors = gather_errors(product_formset)
                for e in errors:
                    messages.error(request, e)
            return redirect("data_group_detail", dg.pk)
        context["product_formset"] = ProductBulkCSVFormSet()

    # This render line must happen after all conditional blocks have been evaluated
    return render(request, template_name, context)


@login_required()
def data_group_documents_table(request, pk):
    dg = get_object_or_404(DataGroup, pk=pk)
    docs = (
        DataDocument.objects.filter(data_group=dg)
        .annotate(extracted=Exists(ExtractedText.objects.filter(pk=OuterRef("pk"))))
        .annotate(product_title=F("products__title"))
        .annotate(
            puc=Case(
                When(products__product_uber_puc__puc__isnull=True, then=Value("")),
                When(
                    products__product_uber_puc__puc__prod_fam="",
                    then=F("products__product_uber_puc__puc__gen_cat"),
                ),
                When(
                    products__product_uber_puc__puc__prod_type="",
                    then=Concat(
                        F("products__product_uber_puc__puc__gen_cat"),
                        Value(" - "),
                        F("products__product_uber_puc__puc__prod_fam"),
                    ),
                ),
                default=Concat(
                    F("products__product_uber_puc__puc__gen_cat"),
                    Value(" - "),
                    F("products__product_uber_puc__puc__prod_fam"),
                    Value(" - "),
                    F("products__product_uber_puc__puc__prod_type"),
                ),
            )
        )
        .annotate(
            classification_method=F(
                "products__product_uber_puc__classification_method__name"
            )
        )
        .annotate(product_id=F("products__id"))
    )
    if dg.is_habits_and_practices:
        docs = docs.prefetch_related("extractedtext__extractedhpdoc")
    doc_list = []
    for doc in docs:
        doc_dict = {
            "id": doc.id,
            "title": doc.title,
            "matched": doc.matched,
            "fileext": os.path.splitext(doc.filename)[1],
            "fileurl": doc.file.url if doc.matched else None,
            "filename": doc.filename,
        }
        if dg.is_composition:
            doc_dict.update(
                {
                    "extracted": doc.extracted,
                    "product_id": doc.product_id,
                    "product_title": doc.product_title,
                    "puc": doc.puc,
                    "classification_method": doc.classification_method,
                    "hidden": "Extracted" if doc.extracted else "Not extracted",
                }
            )
        elif dg.is_habits_and_practices:
            # Get the extraction status
            try:
                doc_dict.update(
                    {"extracted": doc.extractedtext.extractedhpdoc.extraction_completed}
                )
            # If the document is not extracted or the hpdoc does not exist, just set extracted to false.
            except (
                DataDocument.extractedtext.RelatedObjectDoesNotExist,
                ExtractedText.extractedhpdoc.RelatedObjectDoesNotExist,
            ):
                doc_dict.update({"extracted": False})
        else:
            doc_dict["extracted"] = doc.extracted
        doc_list.append(doc_dict)
    return JsonResponse({"data": doc_list})


@login_required()
def data_group_create(
    request, pk, template_name="data_group/datagroup_create_form.html"
):
    datasource = get_object_or_404(DataSource, pk=pk)
    group_key = DataGroup.objects.filter(data_source=datasource).count() + 1
    initial_values = {
        "downloaded_by": request.user,
        "name": f"{datasource} {group_key}",
        "data_source": datasource,
    }
    form = DataGroupForm(
        request.POST or None,
        request.FILES or None,
        user=request.user,
        initial=initial_values,
    )
    grouptypes = GroupType.objects.all()
    for grouptype in grouptypes:
        grouptype.codes = DocumentType.objects.compatible(grouptype)
    context = {
        "form": form,
        "datasource": datasource,
        "grouptypes": grouptypes,
        "csv_headers": RegisterRecordsFormSet.header_cols,
    }

    if request.method == "POST":
        if form.is_valid():
            datagroup = form.save()
            form_data = {
                "register-data_group": datagroup.pk,
                "register-TOTAL_FORMS": 0,
                "register-INITIAL_FORMS": 0,
                "register-MAX_NUM_FORMS": "",
            }
            # gets closed when saved above
            csv_file = request.FILES["csv"].open()
            csv_dict = {"register-bulkformsetfileupload": csv_file}
            rf = RegisterRecordsFormSet(datagroup, form_data, csv_dict)
            if rf.is_valid():
                rf.save()
                return redirect("data_group_detail", pk=datagroup.id)
            else:
                if rf.non_form_errors():
                    for msg in rf.non_form_errors():
                        messages.error(request, msg)
                if not rf.non_form_errors() and rf.errors:
                    errors = gather_errors(rf)
                    for e in errors:
                        messages.error(request, e.strip("__all__:"))
                    # add more here, don't need to add more errors if any non_form_errors exist
                datagroup.delete()
                return render(request, template_name, context)
    return render(request, template_name, context)


@login_required()
def data_group_update(
    request, pk, template_name="data_group/datagroup_update_form.html"
):
    datagroup = get_object_or_404(DataGroup, pk=pk)
    form = DataGroupForm(request.POST or None, instance=datagroup)
    # Do not offer the chance to update the group type
    form.fields.pop("group_type")
    if form.is_valid():
        if form.has_changed():
            form.save()
        return redirect("data_group_detail", pk=datagroup.id)
    form.referer = request.META.get("HTTP_REFERER", None)
    groups = GroupType.objects.all()
    for group in groups:
        group.codes = DocumentType.objects.compatible(group)
    return render(
        request, template_name, {"datagroup": datagroup, "form": form, "groups": groups}
    )


@login_required()
def data_group_delete(
    request, pk, template_name="data_source/datasource_confirm_delete.html"
):
    datagroup = get_object_or_404(DataGroup, pk=pk)
    if request.method == "POST":
        datagroup.delete()
        return redirect("data_group_list")
    return render(request, template_name, {"object": datagroup})


@login_required()
def data_group_delete_products(
    request, pk, template_name="data_group/product_delete_progress.html"
):
    """
    This is an endpoint that deletes Product objects associated with the Data Group
    """
    datagroup = get_object_or_404(DataGroup, pk=pk)
    # schedule async task as it may take sometime to finish the bulk deletion
    delete_task = delete_data_group_products_task.apply_async(
        args=[pk], shadow=f"data_group_products_delete.{pk}"
    )

    return render(
        request,
        template_name,
        {
            "data_group": datagroup,
            "task": delete_task,
            "redirect_to": reverse("data_group_detail", args=[pk]),
        },
    )


@shared_task(bind=True, track_started=True, base=UserTask)
@usertask
def delete_data_group_products_task(self, pk):
    data_group = DataGroup.objects.get(pk=pk)
    with transaction.atomic():
        data_group.get_products().delete()
    return "task done"


@login_required()
def habitsandpractices(request, pk, template_name="data_group/habitsandpractices.html"):
    doc = get_object_or_404(DataDocument, pk=pk)
    script = Script.objects.get(title="Manual (dummy)", script_type="EX")
    extext, created = ExtractedText.objects.get_or_create(
        data_document=doc, extraction_script=script
    )
    if created:
        extext.doc_date = "please add..."
    ExtractedTextForm, HPFormSet = create_detail_formset(doc)
    ext_form = ExtractedTextForm(request.POST or None, instance=extext)
    hp_formset = HPFormSet(request.POST or None, instance=extext, prefix="habits")
    context = {"doc": doc, "ext_form": ext_form, "hp_formset": hp_formset}
    if request.method == "POST" and "save" in request.POST:
        if hp_formset.is_valid():
            hp_formset.save()
        if ext_form.is_valid():
            ext_form.save()
        doc.save()
        context = {"doc": doc, "ext_form": ext_form, "hp_formset": hp_formset}
    return render(request, template_name, context)


@login_required
def download_raw_extracted_records(request, pk):
    datagroup = DataGroup.objects.get(pk=pk)
    et = ExtractedText.objects.filter(data_document__data_group=datagroup).first()
    columnlist = [
        "extracted_text_id",
        "id",
        "raw_cas",
        "raw_chem_name",
        "raw_min_comp",
        "raw_central_comp",
        "raw_max_comp",
        "unit_type__title",
    ]
    if et:
        qs = ExtractedComposition.objects.filter(
            extracted_text__data_document__data_group=datagroup
        ).values(*columnlist)
        return render_to_csv_response(
            qs,
            filename=(datagroup.get_name_as_slug() + "_raw_extracted_records.csv"),
            field_header_map={
                "id": "ExtractedComposition_id",
                "unit_type__title": "unit_type",
            },
            use_verbose_names=False,
        )
    else:
        qs = ExtractedComposition.objects.filter(
            extracted_text__data_document__id=pk
        ).values(*columnlist)
        return render_to_csv_response(
            qs, filename="raw_extracted_records.csv", use_verbose_names=False
        )


@login_required()
def download_unextracted_datadocuments(request, pk):
    datagroup = DataGroup.objects.get(pk=pk)
    documents = (
        DataDocument.objects.filter(data_group=datagroup, extractedtext__isnull=True)
        .exclude(file="")
        .values("pk", "filename")
    )
    filename = datagroup.get_name_as_slug() + "_unextracted_documents.csv"
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=" + filename
    writer = csv.writer(response)
    writer.writerow(datagroup.get_extracted_template_fieldnames())
    for document in documents:
        writer.writerow([document["pk"], document["filename"]])
    return response


@login_required
def download_datadocuments(request, pk):
    datagroup = DataGroup.objects.get(pk=pk)
    documents = DataDocument.objects.filter(data_group=datagroup)
    filename = datagroup.get_name_as_slug() + "_documents.csv"
    return render_to_csv_response(documents, filename=filename, append_datestamp=True)


@login_required
def download_datadocument_zip_file(request, pk):
    datagroup = DataGroup.objects.get(pk=pk)
    files = {doc.filename: doc.file.path for doc in datagroup.datadocument_set.all()}
    filename = f"{datagroup.get_name_as_slug()}_documents.zip"
    return zip_stream(files, filename=filename)


@login_required
def download_registered_datadocuments(request, pk):
    datagroup = DataGroup.objects.filter(pk=pk).first()
    columnlist = [
        "filename",
        "title",
        "document_type",
        "url",
        "organization",
        "subtitle",
        "epa_reg_number",
    ]
    if datagroup:
        columnlist.insert(0, "id")
        filename = datagroup.get_name_as_slug() + "_registered_documents.csv"
        qs = DataDocument.objects.filter(data_group=datagroup).values(*columnlist)
        return render_to_csv_response(
            qs,
            filename=filename,
            field_header_map={"id": "DataDocument_id"},
            use_verbose_names=False,
            encoding="utf-8",
        )
    else:
        qs = DataDocument.objects.filter(data_group_id=0).values(*columnlist)
        return render_to_csv_response(
            qs, filename=datagroup.csv_filename, use_verbose_names=False
        )


@login_required
def get_product_csv_template(request, pk):
    dg = DataGroup.objects.get(pk=pk)
    response = HttpResponse(content_type="text/csv")
    response[
        "Content-Disposition"
    ] = f'attachment; filename="product_csv_template_{pk}.csv"'
    writer = csv.writer(response)
    writer.writerow(
        ["data_document_id", "data_document_filename"]
        + dg.get_product_template_fieldnames()
    )
    for doc in DataDocument.objects.filter(data_group=dg):
        writer.writerow([doc.id, doc.filename])
    return response


@login_required
def download_raw_functional_use_records(request, pk):
    datagroup = DataGroup.objects.get(pk=pk)
    columnlist = ["id", "report_funcuse", "extraction_script__title", "category__title"]
    qs = FunctionalUse.objects.filter(
        chemicals__extracted_text__data_document__data_group=datagroup
    ).values(*columnlist)
    return render_to_csv_response(
        qs,
        filename=(datagroup.get_name_as_slug() + "_raw_functional_use_records.csv"),
        field_header_map={
            "extraction_script__title": "extraction_script",
            "category__title": "category_title",
        },
        use_verbose_names=False,
    )


@login_required()
def data_group_tracking(request, template_name="data_group/data_group_tracking.html"):
    datagroups = (
        DataGroup.objects.all()
        .select_related("data_source", "group_type")
        .prefetch_related("curation_steps")
        .annotate(doc_count=Count("datadocument"))
        .order_by("name")
    )
    curationsteps = CurationStep.objects.all().values("name", "id")
    data = {"datagroups": list(datagroups), "curationsteps": list(curationsteps)}

    return render(request, template_name, data)


@login_required()
def edit_data_group_tracking(
    request, dg_pk, template_name="data_group/data_group_tracking_edit.html"
):
    datagroup = get_object_or_404(DataGroup, pk=dg_pk)
    form = DataGroupWorkflowForm(request.POST or None, instance=datagroup)
    co_count = ExtractedComposition.objects.filter(
        extracted_text__data_document__data_group=datagroup
    ).count()
    data = {"datagroup": datagroup, "form": form, "co_count": co_count}

    if request.method == "POST":
        if form.is_valid():
            form.save()
            return redirect("data_group_tracking")
    return render(request, template_name, data)


@login_required()
def set_data_group_no_co_data(request, dg_pk):
    datagroup = get_object_or_404(DataGroup, pk=dg_pk)
    if request.method == "POST":
        with transaction.atomic():
            # reset the flag for all related documents
            ExtractedComposition.objects.filter(
                extracted_text__data_document__data_group=datagroup
            ).update(has_composition_data=False)
            # set the step status to n/a
            step = CurationStep.objects.filter(name="Composition Cleaned").first()
            wf = DataGroupCurationWorkflow.objects.filter(
                data_group=datagroup, curation_step=step
            ).first()
            if wf is not None:
                if wf.step_status != "N":
                    wf.step_status = "N"
                    wf.save()
            else:
                DataGroupCurationWorkflow.objects.create(
                    data_group=datagroup, curation_step=step, step_status="N"
                )
            messages.success(
                request,
                "The Has Composition Data flag has been reset for all chemicals",
            )
    return redirect("data_group_tracking_edit", dg_pk=dg_pk)


@register.filter(name="get_current_step_status")
def get_current_step_status(datagroup, step_id):
    for step in datagroup.curation_steps.all():
        if step.curation_step_id == step_id:
            return step.step_status
    return "I"
