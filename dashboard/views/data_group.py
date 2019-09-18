import csv
from djqscsv import render_to_csv_response
from pathlib import Path
import zipfile
from django.db.models import CharField, Exists, F, OuterRef, Value as V
from django.db.models.functions import StrIndex, Substr
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.files import File
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404

from dashboard.forms import DataGroupForm, create_detail_formset
from dashboard.forms.data_group import (
    BulkAssignProdForm,
    CleanCompFormSet,
    ExtractFileFormSet,
    UploadDocsForm,
)
from dashboard.models import (
    ExtractedText,
    Script,
    ExtractedChemical,
    DataSource,
    DocumentType,
    GroupType,
    DataDocument,
    DataGroup,
)
from dashboard.utils import gather_errors
from factotum.settings import MEDIA_URL


@login_required()
def data_group_list(request, code=None, template_name="data_group/datagroup_list.html"):
    if code:
        group = get_object_or_404(GroupType, code=code)
        datagroup = DataGroup.objects.filter(group_type=group)
    else:
        datagroup = DataGroup.objects.all()
    data = {"object_list": datagroup}
    return render(request, template_name, data)


@login_required()
def data_group_detail(request, pk, template_name="data_group/datagroup_detail.html"):
    dg = get_object_or_404(DataGroup, pk=pk)
    tabledata = {
        "fsid": dg.fs_id,
        "boolComp": dg.is_composition,
        "boolHab": dg.is_habits_and_practices,
        "numregistered": dg.registered_docs(),
        "nummatched": dg.matched_docs(),
        "numextracted": dg.extracted_docs(),
    }
    context = {
        "datagroup": dg,
        "tabledata": tabledata,
        "clean_comp_data_fieldnames": ", ".join(
            [
                "ExtractedChemical_id" if x == "id" else x
                for x in dg.get_clean_comp_data_fieldnames()
            ]
        ),
        "uploaddocs_form": None,
        "extfile_form": None,
        "cleancomp_form": None,
        "bulkassignprod_form": None,
    }
    # TODO: Lots of boilerplate code here.
    if dg.include_upload_docs_form():
        if "uploaddocs-submit" in request.POST:
            form = UploadDocsForm(dg, request.POST, request.FILES)
            context["uploaddocs_form"] = UploadDocsForm(dg, request.POST, request.FILES)
            if form.is_valid():
                num_saved = form.save()
                if num_saved > 1:
                    o_str = "documents"
                else:
                    o_str = "document"
                msg = "%d %s uploaded successfully." % (num_saved, o_str)
                messages.success(request, msg)
            else:
                errors = gather_errors(form)
                for e in errors:
                    messages.error(request, e)
        else:
            context["uploaddocs_form"] = UploadDocsForm(dg)

    if dg.include_extract_form():
        if "extfile-submit" in request.POST:
            form = ExtractFileFormSet(dg, request.POST, request.FILES)
            context["extfile_form"] = ExtractFileFormSet(dg, request.POST)
            if form.is_valid():
                num_saved = form.save()
                if num_saved > 1:
                    o_str = "extracted records"
                else:
                    o_str = "extracted record"
                msg = "%d %s uploaded successfully." % (num_saved, o_str)
                messages.success(request, msg)
            else:
                errors = gather_errors(form)
                for e in errors:
                    messages.error(request, e)
        else:
            context["extfile_form"] = ExtractFileFormSet(dg)

    if dg.include_clean_comp_data_form():
        if "cleancomp-submit" in request.POST:
            form = CleanCompFormSet(dg, request.POST, request.FILES)
            context["cleancomp_form"] = CleanCompFormSet(dg, request.POST)
            if form.is_valid():
                num_saved = form.save()
                if num_saved > 1:
                    o_str = "clean composition data records"
                else:
                    o_str = "clean composition data record"
                msg = "%d %s uploaded successfully." % (num_saved, o_str)
                messages.success(request, msg)
            else:
                errors = gather_errors(form)
                for e in errors:
                    messages.error(request, e)
        else:
            context["cleancomp_form"] = CleanCompFormSet(dg)

    if dg.include_bulk_assign_form():
        if "bulkassignprod-submit" in request.POST:
            form = BulkAssignProdForm(dg, request.POST, request.FILES)
            if form.is_valid():
                num_saved = form.save()
                if num_saved > 1:
                    o_str = "products"
                else:
                    o_str = "product"
                msg = "%d %s created successfully." % (num_saved, o_str)
                messages.success(request, msg)
            else:
                errors = gather_errors(form)
                for e in errors:
                    messages.error(request, e)
        else:
            context["bulkassignprod_form"] = BulkAssignProdForm(dg)

    return render(request, template_name, context)


@login_required()
def data_group_documents_table(request, pk):
    dg = get_object_or_404(DataGroup, pk=pk)
    docs = (
        DataDocument.objects.filter(data_group=dg)
        .annotate(extracted=Exists(ExtractedText.objects.filter(pk=OuterRef("pk"))))
        .annotate(
            fileext=Substr(
                "filename", (StrIndex("filename", V("."))), output_field=CharField()
            )
        )
        .annotate(product_title=F("products__title"))
        .annotate(product_id=F("products__id"))
    )
    if dg.is_habits_and_practices:
        doc_vals = docs.values("id", "title", "matched", "fileext")
    elif dg.is_composition:
        doc_vals = docs.values(
            "id",
            "title",
            "matched",
            "fileext",
            "extracted",
            "product_id",
            "product_title",
        )
    else:
        doc_vals = docs.values("id", "title", "matched", "fileext", "extracted")
    return JsonResponse({"data": list(doc_vals)})


@login_required()
def data_group_create(request, pk, template_name="data_group/datagroup_form.html"):
    datasource = get_object_or_404(DataSource, pk=pk)
    group_key = DataGroup.objects.filter(data_source=datasource).count() + 1
    initial_values = {
        "downloaded_by": request.user,
        "name": f"{datasource} {group_key}",
        "data_source": datasource,
    }
    if request.method == "POST":
        form = DataGroupForm(
            request.POST, request.FILES, user=request.user, initial=initial_values
        )
        if form.is_valid():
            datagroup = form.save()
            info = datagroup.csv.open("rU")
            table = csv.DictReader(info)
            good_fields = ["filename", "title", "document_type", "url", "organization"]
            if not table.fieldnames == good_fields:
                datagroup.csv.close()
                datagroup.delete()
                return render(
                    request,
                    template_name,
                    {
                        "field_error": table.fieldnames,
                        "good_fields": good_fields,
                        "form": form,
                    },
                )
            text = ["DataDocument_id," + ",".join(table.fieldnames) + "\n"]
            errors = []
            filenames = []
            count = 0
            for line in table:  # read every csv line, create docs for each
                count += 1
                doc_type = None
                code = line["document_type"]
                if line["filename"] == "":
                    errors.append([count, "Filename can't be empty!"])
                    continue
                if len(line["filename"]) > 255:
                    errors.append([count, "Filename too long!"])
                    continue
                if line["filename"] in filenames:
                    errors.append([count, "Duplicate filename found in csv"])
                    continue
                if line["title"] == "":  # updates title in line object
                    line["title"] = line["filename"].split(".")[0]
                a = bool(code)
                b = a and DocumentType.objects.filter(code=code).exists()
                if b:
                    doc_type = DocumentType.objects.get(code=code)
                elif a & ~b:
                    errors.append([count, "DocumentType code doesn't exist."])

                filenames.append(line["filename"])
                doc = DataDocument(
                    filename=line["filename"],
                    title=line["title"],
                    document_type=doc_type,
                    url=line["url"],
                    organization=line["organization"],
                    data_group=datagroup,
                )
                doc.save()
                # update line to hold the pk for writeout
                text.append(str(doc.pk) + "," + ",".join(line.values()) + "\n")
            if errors:
                datagroup.csv.close()
                datagroup.delete()
                return render(
                    request, template_name, {"line_errors": errors, "form": form}
                )
            # Save the DG to make sure the pk exists
            datagroup.save()
            # Let's even write the csv first
            with open(datagroup.csv.path, "w") as f:
                myfile = File(f)
                myfile.write("".join(text))
            # Let's explicitly use the full path for writing of the zipfile
            uid = str(datagroup.fs_id)
            new_zip_name = Path(settings.MEDIA_URL) / uid / (uid + ".zip")
            new_zip_path = Path(settings.MEDIA_ROOT) / uid / (uid + ".zip")
            zf = zipfile.ZipFile(str(new_zip_path), "w", zipfile.ZIP_DEFLATED)
            datagroup.zip_file = new_zip_name
            zf.close()
            datagroup.save()
            return redirect("data_group_detail", pk=datagroup.id)
    else:
        groups = GroupType.objects.all()
        for group in groups:
            group.codes = DocumentType.objects.compatible(group)
        form = DataGroupForm(user=request.user, initial=initial_values)
    context = {"form": form, "datasource": datasource, "groups": groups}
    return render(request, template_name, context)


@login_required()
def data_group_update(request, pk, template_name="data_group/datagroup_form.html"):
    datagroup = get_object_or_404(DataGroup, pk=pk)
    form = DataGroupForm(request.POST or None, instance=datagroup)
    if form.is_valid():
        if form.has_changed():
            form.save()
        return redirect("data_group_detail", pk=datagroup.id)
    form.referer = request.META.get("HTTP_REFERER", None)
    # updated 07/03/2019 - now none of the group types should be allowed to change (was ones with extracted docs only)
    form.fields["group_type"].disabled = True
    groups = GroupType.objects.all()
    for group in groups:
        group.codes = DocumentType.objects.compatible(group)
    return render(
        request,
        template_name,
        {"datagroup": datagroup, "form": form, "media": MEDIA_URL, "groups": groups},
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
def habitsandpractices(request, pk, template_name="data_group/habitsandpractices.html"):
    doc = get_object_or_404(DataDocument, pk=pk)
    script = Script.objects.get(title="Manual (dummy)", script_type="EX")
    extext, created = ExtractedText.objects.get_or_create(
        data_document=doc, extraction_script=script
    )
    if created:
        extext.doc_date = "please add..."
    ExtractedTextForm, HPFormSet = create_detail_formset(doc)
    # print(f'running habitsandpractices() on %s inside views/data_group.py' % doc)
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
        qs = ExtractedChemical.objects.filter(
            extracted_text__data_document__data_group=datagroup
        ).values(*columnlist)
        return render_to_csv_response(
            qs,
            filename=(datagroup.get_name_as_slug() + "_raw_extracted_records.csv"),
            field_header_map={"id": "ExtractedChemical_id"},
            use_verbose_names=False,
        )
    else:
        qs = ExtractedChemical.objects.filter(
            extracted_text__data_document__id=pk
        ).values(*columnlist)
        return render_to_csv_response(
            qs, filename="raw_extracted_records.csv", use_verbose_names=False
        )


@login_required()
def download_unextracted_datadocuments(request, pk):
    datagroup = DataGroup.objects.get(pk=pk)
    documents = DataDocument.objects.filter(
        data_group=datagroup, matched=True, extractedtext__isnull=True
    ).values("pk", "filename")
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
    zip_file_name = f"{datagroup.fs_id}.zip"
    zip_file = open(datagroup.get_zip_url(), "rb")
    response = HttpResponse(zip_file, content_type="application/zip")
    response["Content-Disposition"] = "attachment; filename=%s" % zip_file_name
    return response


@login_required
def download_registered_datadocuments(request, pk):
    datagroup = DataGroup.objects.filter(pk=pk).first()
    columnlist = ["filename", "title", "document_type", "url", "organization"]
    if datagroup:
        columnlist.insert(0, "id")
        filename = datagroup.get_name_as_slug() + "_registered_documents.csv"
        qs = DataDocument.objects.filter(data_group=datagroup).values(*columnlist)
        return render_to_csv_response(
            qs,
            filename=filename,
            field_header_map={"id": "DataDocument_id"},
            use_verbose_names=False,
        )
    else:
        qs = DataDocument.objects.filter(data_group_id=0).values(*columnlist)
        return render_to_csv_response(
            qs, filename="registered_documents.csv", use_verbose_names=False
        )
