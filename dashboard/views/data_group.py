import csv
import zipfile
from djqscsv import render_to_csv_response
from pathlib import Path

from django.db.models import Exists, F, OuterRef, Max
from django.conf import settings
from django.core.files import File
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse

from factotum.settings import MEDIA_URL
from dashboard.models import (
    Product,
    ProductDocument,
    ExtractedText,
    Script,
    WeightFractionType,
    UnitType,
    ExtractedListPresence,
    ExtractedChemical,
    Ingredient,
    DataSource,
    DocumentType,
    GroupType,
    DataDocument,
    DataGroup,
)
from dashboard.forms import (
    DataGroupForm,
    ExtractionScriptForm,
    CleanCompDataForm,
    create_detail_formset,
)
from dashboard.utils import get_extracted_models, clean_dict, update_fields


@login_required()
def data_group_list(request, template_name="data_group/datagroup_list.html"):
    datagroup = DataGroup.objects.all()
    data = {}
    data["object_list"] = datagroup
    return render(request, template_name, data)


@login_required()
def data_group_detail(request, pk, template_name="data_group/datagroup_detail.html"):
    datagroup = get_object_or_404(DataGroup, pk=pk)
    extracted_text = ExtractedText.objects.filter(pk=OuterRef("pk"))
    documents = (
        DataDocument.objects.filter(data_group=datagroup)
        .annotate(extracted=Exists(extracted_text))
        .annotate(product_id=F("products__id"))
        .annotate(product_title=F("products__title"))
    )
    extract_form = (
        ExtractionScriptForm(dg_type=datagroup.type)
        if datagroup.include_extract_form()
        else None
    )
    clean_comp_data_form = (
        CleanCompDataForm() if datagroup.include_clean_comp_data_form() else None
    )
    store = settings.MEDIA_URL + str(datagroup.fs_id)
    context = {
        "datagroup": datagroup,
        "documents": documents,
        "extract_form": extract_form,
        "clean_comp_data_form": clean_comp_data_form,
        "bulk_product_count": documents.filter(product_id=None).count(),
        "ext_err": {},
        "clean_comp_err": {},
        "msg": "",
    }
    if request.method == "POST" and "upload" in request.POST:
        # match filename to pdf name
        matched_files = [
            f
            for d in documents
            for f in request.FILES.getlist("multifiles")
            if f.name == d.filename
        ]
        if not matched_files:
            context["msg"] = (
                "There are no matching records in the " "selected directory."
            )
            return render(request, template_name, context)
        zf = zipfile.ZipFile(datagroup.zip_file, "a", zipfile.ZIP_DEFLATED)
        while matched_files:
            f = matched_files.pop(0)
            doc = DataDocument.objects.get(filename=f.name, data_group=datagroup.pk)
            if doc.matched:
                continue
            doc.matched = True
            doc.save()
            fs = FileSystemStorage(store + "/pdf")
            afn = doc.get_abstract_filename()
            fs.save(afn, f)
            zf.write(store + "/pdf/" + afn, afn)
        zf.close()
        form = datagroup.include_extract_form()
        # update docs so it appears in the template table w/ "matched" docs
        context["documents"] = datagroup.datadocument_set.all()
        context["extract_form"] = form
        context["msg"] = "Matching records uploaded successfully."
    if request.method == "POST" and "extract_button" in request.POST:
        extract_form = ExtractionScriptForm(
            request.POST, request.FILES, dg_type=datagroup.type
        )
        if extract_form.is_valid():
            csv_file = request.FILES.get("extract_file")
            script_pk = int(request.POST["script_selection"])
            script = Script.objects.get(pk=script_pk)
            info = [x.decode("ascii", "ignore") for x in csv_file.readlines()]
            table = csv.DictReader(info)
            missing = list(
                set(datagroup.get_extracted_template_fieldnames())
                - set(table.fieldnames)
            )
            if missing:  # column names are NOT a match, send back to user
                context["msg"] = (
                    "The following columns need to be added or "
                    f"renamed in the csv: {missing}"
                )
                return render(request, template_name, context)
            good_records = []
            ext_parent, ext_child = get_extracted_models(datagroup.type)
            for i, row in enumerate(csv.DictReader(info)):
                d = documents.get(pk=int(row["data_document_id"]))
                d.raw_category = row.pop("raw_category")
                wft = request.POST.get("weight_fraction_type", None)
                if wft:  # this signifies 'Composition' type
                    w = "weight_fraction_type"
                    row[w] = WeightFractionType.objects.get(pk=int(wft))
                    if row["unit_type"]:
                        unit_type_id = int(row["unit_type"])
                        row["unit_type"] = UnitType.objects.get(pk=unit_type_id)
                    else:
                        del row["unit_type"]
                    rank = row["ingredient_rank"]
                    row["ingredient_rank"] = None if rank == "" else rank
                ext, created = ext_parent.objects.get_or_create(
                    data_document=d, extraction_script=script
                )
                if not created and ext.one_to_one_check(row):
                    # check that there is a 1:1 relation ExtParent and DataDoc
                    col = "cat_code" if hasattr(ext, "cat_code") else "prod_name"
                    err_msg = ['must be 1:1 with "data_document_id".']
                    context["ext_err"][i + 1] = {col: err_msg}
                if created:
                    update_fields(row, ext)
                row["extracted_text"] = ext
                if ext_child == ExtractedListPresence:
                    row["extracted_cpcat"] = ext.extractedtext_ptr
                row = clean_dict(row, ext_child)
                try:
                    ext.full_clean()
                    ext.save()
                    record = ext_child(**row)
                    record.full_clean()
                    good_records.append((d, ext, record))
                except ValidationError as e:
                    context["ext_err"][i + 1] = e.message_dict
            if context["ext_err"]:  # if errors, send back with errors
                [e[1].delete() for e in good_records]  # delete any created exts
                return render(request, template_name, context)
            if not context["ext_err"]:  # no saving until all errors are removed
                for doc, text, record in good_records:
                    # doc.extracted = True
                    doc.save()
                    text.save()
                    record.save()
                fs = FileSystemStorage(store)
                fs.save(str(datagroup) + "_extracted.csv", csv_file)
                context["msg"] = (
                    f"{len(good_records)} extracted records " "uploaded successfully."
                )
                context["extract_form"] = datagroup.include_extract_form()
    if request.method == "POST" and "bulk" in request.POST:
        docs_needing_products = documents.filter(product_id=None)
        stub = Product.objects.all().aggregate(Max("id"))["id__max"] + 1
        for doc in docs_needing_products:
            # Try to name the new product from the ExtractedText record's prod_name
            try:
                new_prod_title = None
                ext = ExtractedText.objects.get(data_document_id=doc.id)
                if ext.prod_name:
                    new_prod_title = ext.prod_name
            except ExtractedText.DoesNotExist:
                new_prod_title = None
            # If the ExtractedText record can't provide a title, use the DataDocument's title
            if not new_prod_title:
                if doc.title:
                    new_prod_title = "%s stub" % doc.title
                else:
                    new_prod_title = "unknown"
            product = Product.objects.create(
                title=new_prod_title,
                upc=f"stub_{stub}",
                data_source_id=doc.data_group.data_source_id,
            )
            ProductDocument.objects.create(product=product, document=doc)
            stub += 1
        context["bulk"] = 0
    if request.method == "POST" and "clean_comp_data_button" in request.POST:
        clean_comp_data_form = CleanCompDataForm(request.POST, request.FILES)
        if clean_comp_data_form.is_valid():
            script_pk = int(request.POST["script_selection"])
            script = Script.objects.get(pk=script_pk)
            csv_file = request.FILES.get("clean_comp_data_file")
            info = [x.decode("ascii", "ignore") for x in csv_file.readlines()]
            table = csv.DictReader(info)
            missing = list(
                set(datagroup.get_clean_comp_data_fieldnames()) - set(table.fieldnames)
            )
            if missing:  # column names are NOT a match, send back to user
                context["clean_comp_data_form"].collapsed = False
                context["msg"] = (
                    "The following columns need to be added or "
                    f"renamed in the csv: {missing}"
                )
                return render(request, template_name, context)

            good_records = []
            for i, row in enumerate(csv.DictReader(info)):
                try:
                    extracted_chemical = ExtractedChemical.objects.get(
                        rawchem_ptr=int(row["id"])
                    )
                except ExtractedChemical.DoesNotExist as e:
                    extracted_chemical = None
                    context["clean_comp_err"][i + 1] = {
                        "id": [
                            "No ExtractedChemical matches rawchem_ptr_id " + row["id"]
                        ]
                    }
                    print("No ExtractedChemical matches rawchem_ptr_id %s" % row["id"])
                try:
                    ingredient = Ingredient.objects.get(
                        rawchem_ptr=extracted_chemical.rawchem_ptr
                    )
                except Ingredient.DoesNotExist as e:
                    ingredient = Ingredient(rawchem_ptr=extracted_chemical.rawchem_ptr)
                ingredient.lower_wf_analysis = row["lower_wf_analysis"]
                ingredient.central_wf_analysis = row["central_wf_analysis"]
                ingredient.upper_wf_analysis = row["upper_wf_analysis"]
                ingredient.script = script
                try:
                    ingredient.full_clean()
                except ValidationError as e:
                    context["clean_comp_err"][i + 1] = e.message_dict
                good_records.append(ingredient)
            if context["clean_comp_err"]:  # if errors, send back with errors
                context["clean_comp_data_form"].collapsed = False
                return render(request, template_name, context)
            if not context["clean_comp_err"]:  # no saving until all errors are removed
                for ingredient in good_records:
                    ingredient.save()
                context["msg"] = (
                    f"{len(good_records)} clean composition data records "
                    "uploaded successfully."
                )
                context[
                    "clean_comp_data_form"
                ] = datagroup.include_clean_comp_data_form()
        else:
            context["clean_comp_data_form"].collapsed = False
    return render(request, template_name, context)


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
        return redirect('data_group_detail', pk=datagroup.id)
    form.referer = request.META.get('HTTP_REFERER', None)
    # updated 07/03/2019 - now none of the group types should be allowed to change (was ones with extracted docs only)
    form.fields['group_type'].disabled = True
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
