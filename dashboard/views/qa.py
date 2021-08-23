import json

from celery import shared_task
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q, Max, OuterRef, Exists
from django.db.models.functions import Greatest, Coalesce
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.http import is_safe_url
from django.utils.timesince import timesince
from django_datatables_view.base_datatable_view import BaseDatatableView

from celery_usertask.tasks import UserTask, usertask
from dashboard.forms import create_detail_formset, QANotesForm, DocumentTypeForm
from dashboard.forms.forms import QASummaryNoteForm
from dashboard.views.data_document import cards_detail
from dashboard.models import (
    Script,
    DataGroup,
    DataDocument,
    ExtractedCPCat,
    ExtractedText,
    QANotes,
    QAGroup,
    DocumentType,
    RawChem,
    AuditLog,
    GroupType,
)


@login_required()
def qa_extractionscript_index(request, template_name="qa/extraction_script_index.html"):
    extractedtext_count = Count("extractedtext__extraction_script")
    qa_group_count = Count("extractedtext__qa_group")
    qa_complete_count = Count("extractedtext", filter=Q(extractedtext__qa_checked=True))
    percent_complete = (qa_complete_count / qa_group_count) * 100
    # defaults to composition type
    group_type_code = request.GET.get("group_type", "CO")
    group_type = GroupType.objects.filter(code=group_type_code).first()
    extraction_scripts = (
        Script.objects.filter(script_type="EX")
        .filter(
            extractedtext__data_document__data_group__group_type__code=group_type_code
        )
        .exclude(title="Manual (dummy)")
        .annotate(extractedtext_count=extractedtext_count)
        .annotate(percent_complete=percent_complete)
        .annotate(qa_group_count=qa_group_count)
        .filter(extractedtext_count__gt=0)
    )
    return render(
        request,
        template_name,
        {"extraction_scripts": extraction_scripts, "group_type": group_type},
    )


@login_required()
def qa_chemicalpresence_index(request, template_name="qa/chemical_presence_index.html"):
    datagroups = (
        DataGroup.objects.filter(group_type__code="CP")
        .annotate(datadocument_count=Count("datadocument"))
        .annotate(
            approved_count=Count(
                "datadocument__extractedtext",
                filter=Q(datadocument__extractedtext__qa_checked=True),
            )
        )
        .annotate(extracted_count=Count("datadocument__extractedtext"))
        .filter(extracted_count__gt=0)
    )

    return render(request, template_name, {"datagroups": datagroups})


@login_required()
def qa_manual_composition_index(
    request, template_name="qa/qa_manual_composition_index.html"
):
    MANUAL_SCRIPT_ID = (
        Script.objects.filter(title="Manual (dummy)", script_type="EX").first().id
    )

    datagroups = (
        DataGroup.objects.filter(group_type__code="CO")
        .annotate(
            datadocument_count=Count(
                "datadocument__extractedtext",
                filter=Q(
                    datadocument__extractedtext__extraction_script__id=MANUAL_SCRIPT_ID
                ),
            ),
            approved_count=Count(
                "datadocument__extractedtext",
                filter=Q(
                    datadocument__extractedtext__extraction_script__id=MANUAL_SCRIPT_ID,
                    datadocument__extractedtext__qa_checked=True,
                ),
            ),
        )
        .filter(datadocument_count__gt=0)
    )

    return render(request, template_name, {"datagroups": datagroups})


@login_required()
def qa_manual_composition_summary(
    request, pk, template_name="qa/qa_manual_composition_summary.html"
):
    MANUAL_SCRIPT_ID = (
        Script.objects.filter(title="Manual (dummy)", script_type="EX").first().id
    )

    datagroup = (
        DataGroup.objects.filter(pk=pk)
        .annotate(
            document_count=Count(
                "datadocument__extractedtext",
                filter=Q(
                    datadocument__extractedtext__extraction_script__id=MANUAL_SCRIPT_ID
                ),
            )
        )
        .annotate(
            qa_complete_count=Count(
                "datadocument__extractedtext",
                filter=Q(
                    datadocument__extractedtext__extraction_script__id=MANUAL_SCRIPT_ID,
                    datadocument__extractedtext__qa_checked=True,
                ),
            )
        )
        .annotate(
            qa_note_count=Count(
                "datadocument__extractedtext__qanotes__qa_notes",
                filter=Q(
                    datadocument__extractedtext__extraction_script__id=MANUAL_SCRIPT_ID
                )
                & ~Q(datadocument__extractedtext__qanotes__qa_notes=""),
            )
        )
    ).first()
    datagroup.qa_incomplete_count = (
        datagroup.document_count - datagroup.qa_complete_count
    )
    noteform = QASummaryNoteForm(instance=datagroup)
    return render(
        request,
        template_name,
        {
            "datagroup": datagroup,
            "document_table_url": reverse(
                "qa_manual_composition_summary_table", args=[pk]
            ),
            "noteform": noteform,
        },
    )


@login_required()
def qa_chemicalpresence_group(request, pk, template_name="qa/chemical_presence.html"):
    datagroup = DataGroup.objects.get(pk=pk)
    if datagroup.group_type.code != "CP":
        raise ValidationError("This DataGroup is not of a ChemicalPresence type")
    extractedcpcats = ExtractedCPCat.objects.filter(data_document__data_group=datagroup)
    return render(
        request,
        template_name,
        {"datagroup": datagroup, "extractedcpcats": extractedcpcats},
    )


@login_required()
def qa_chemicalpresence_summary(
    request, pk, template_name="qa/chemical_presence_summary.html"
):
    datagroup = DataGroup.objects.get(pk=pk)
    if datagroup.group_type.code != "CP":
        raise ValidationError("This DataGroup is not of a ChemicalPresence type")

    datagroup = (
        DataGroup.objects.filter(pk=pk)
        .annotate(document_count=Count("datadocument"))
        .annotate(
            qa_complete_count=Count(
                "datadocument__extractedtext",
                filter=Q(datadocument__extractedtext__qa_checked=True),
            )
        )
        .annotate(
            qa_note_count=Count(
                "datadocument__extractedtext__qanotes__qa_notes",
                filter=~Q(datadocument__extractedtext__qanotes__qa_notes=""),
            )
        )
    ).first()
    datagroup.qa_incomplete_count = (
        datagroup.document_count - datagroup.qa_complete_count
    )
    noteform = QASummaryNoteForm(instance=datagroup)
    return render(
        request,
        template_name,
        {
            "datagroup": datagroup,
            "document_table_url": reverse(
                "qa_chemical_presence_summary_table", args=[pk]
            ),
            "noteform": noteform,
        },
    )


@login_required()
def qa_extraction_script(request, pk, template_name="qa/extraction_script.html"):
    """
    The user reviews the extracted text and checks whether it was properly converted to data
    """
    script = get_object_or_404(Script, pk=pk)
    # If the Script has no related ExtractedText objects, redirect back to the QA index
    if ExtractedText.objects.filter(extraction_script=script).count() == 0:
        return redirect("qa_extractionscript_index")
    qa_group = script.get_or_create_qa_group()
    texts = (
        ExtractedText.objects.filter(qa_group=qa_group, qa_checked=False)
        .select_related("data_document__data_group__group_type")
        .annotate(chemical_count=Count("rawchem"))
        .annotate(chemical_updated_at=Max("rawchem__updated_at"))
    )
    return render(
        request,
        template_name,
        {"extractionscript": script, "extractedtexts": texts, "qagroup": qa_group},
    )


@login_required()
def qa_manual_composition_script(
    request, pk, template_name="qa/qa_manual_composition.html"
):
    datagroup = DataGroup.objects.get(pk=pk)
    if datagroup.group_type.code != "CO":
        raise ValidationError("This DataGroup is not of a Composition type")

    MANUAL_SCRIPT_ID = (
        Script.objects.filter(title="Manual (dummy)", script_type="EX").first().id
    )

    extractedtexts = (
        ExtractedText.objects.filter(
            data_document__data_group=datagroup, qa_checked=False
        )
        .prefetch_related("data_document__data_group")
        .filter(extraction_script__id=MANUAL_SCRIPT_ID)
        .annotate(chemical_count=Count("rawchem"))
        .annotate(chemical_updated_at=Max("rawchem__updated_at"))
    )
    return render(
        request,
        template_name,
        {"datagroup": datagroup, "extractedtexts": extractedtexts},
    )


@login_required()
def qa_extraction_script_summary(
    request, pk, template_name="qa/extraction_script_summary.html"
):
    datadocument_count = Count("extractedtext__extraction_script")
    qa_complete_extractedtext_count = Count(
        "extractedtext", filter=Q(extractedtext__qa_checked=True)
    )
    qa_note_count = Count(
        "extractedtext__qanotes__qa_notes",
        filter=~Q(extractedtext__qanotes__qa_notes=""),
    )
    script = (
        Script.objects.filter(pk=pk)
        .annotate(extractedtext_count=datadocument_count)
        .annotate(qa_complete_extractedtext_count=qa_complete_extractedtext_count)
        .annotate(
            qa_incomplete_extractedtext_count=datadocument_count
            - qa_complete_extractedtext_count
        )
        .annotate(qa_note_count=qa_note_count)
        .first()
    )
    qa_group = script.get_or_create_qa_group()
    noteform = QASummaryNoteForm(instance=script)

    return render(
        request,
        template_name,
        {
            "extractionscript": script,
            "qa_group": qa_group,
            "document_table_url": reverse(
                "qa_extraction_script_summary_table", args=[pk]
            ),
            "noteform": noteform,
        },
    )


class SummaryTable(BaseDatatableView):
    """This table is focused on extracted texts but built on a specific script's extracted texts.
    There is no model but each row should refer to an ExtractedText.
    """

    columns = [
        "data_document__data_group__name",
        "data_document__title",
        "qanotes__qa_notes",
        "qa_checked",
        "rawchem_count",
        "last_updated",
    ]

    class Meta:
        abstract = True

    def get_filter_method(self):
        """ Returns preferred filter method """
        return self.FILTER_ICONTAINS

    def render_column(self, row, column):
        if column == "data_document__data_group__name":
            return f"""<a href="{reverse("data_group_detail", args=[row.data_document.data_group.id])}">
                            {row.data_document.data_group}
                        </a>"""
        if column == "data_document__title":
            return f"""<a href="{reverse("data_document", args=[row.pk])}">
                            {row.data_document}
                        </a>"""
        if column == "qanotes__qa_notes":
            try:
                return row.qanotes.qa_notes
            except QANotes.DoesNotExist:
                return None
        if column == "qa_checked":
            return "Yes" if row.qa_checked else "No"
        if column == "rawchem_count":
            return row.rawchem_count
        elif column == "last_updated":
            if row.last_updated is None:
                return "No Records"
            else:
                return f"""<a title="audit log"
                              href="{reverse("document_audit_log", args=[row.pk])}"
                              data-toggle="modal"
                              data-target="#document-audit-log-modal">
                                Last updated {timesince(row.last_updated)} ago
                            </a>"""
        super().render_column(row, column)

    def get_initial_queryset(self):
        """The values that are used to make up this table are "valid" extracted texts.
        For an extracted text to be considered valid, it must have one of the following:
            - A QA Note
            - A raw chem with an audit log
        There are checked against the update/create at fields.

        :return: QuerySet of all valid ExtractedText rows
        """
        rc_log_subquery = AuditLog.objects.filter(
            extracted_text_id=OuterRef("pk"), action__in=["U", "D"]
        ).values("id")
        qa_subquery = QANotes.objects.filter(extracted_text=OuterRef("pk")).values("id")

        qs = (
            self.get_extractedtext_queryset()
            .annotate(has_qanotes=Exists(qa_subquery))
            .annotate(has_updated_rc=Exists(rc_log_subquery))
            .filter(Q(has_qanotes=True) | Q(has_updated_rc=True))
            .prefetch_related("rawchem")
            .select_related("qanotes", "data_document")
            .annotate(last_updated_rc=Max("rawchem__updated_at"))
            .annotate(
                last_updated=Greatest(
                    Coalesce(
                        "updated_at", "data_document__updated_at", "last_updated_rc"
                    ),
                    Coalesce(
                        "data_document__updated_at", "last_updated_rc", "updated_at"
                    ),
                    Coalesce(
                        "last_updated_rc", "updated_at", "data_document__updated_at"
                    ),
                )
            )
            .annotate(rawchem_count=Count("rawchem", distinct=True))
            .all()
        )
        return qs


class ScriptSummaryTable(SummaryTable):
    def get(self, request, pk, *args, **kwargs):
        """This PK should be an Script pk"""
        self.pk = pk
        return super().get(request, *args, **kwargs)

    def get_extractedtext_queryset(self):
        return Script.objects.get(pk=self.pk).extractedtext_set


class ChemicalPresenceSummaryTable(SummaryTable):
    def get(self, request, pk, *args, **kwargs):
        """This PK should be a chemical presence data group pk"""
        self.pk = pk
        return super().get(request, *args, **kwargs)

    def get_extractedtext_queryset(self):
        return ExtractedText.objects.filter(data_document__data_group__id=self.pk)


class ManualCompositionDataGroupSummaryTable(SummaryTable):
    def get(self, request, pk, *args, **kwargs):
        """This PK should be a data group pk"""
        self.pk = pk
        return super().get(request, *args, **kwargs)

    def get_extractedtext_queryset(self):
        MANUAL_SCRIPT_ID = (
            Script.objects.filter(title="Manual (dummy)", script_type="EX").first().id
        )
        return ExtractedText.objects.filter(
            data_document__data_group__id=self.pk, extraction_script=MANUAL_SCRIPT_ID
        )


@login_required()
def extracted_text_qa(request, pk, template_name="qa/extracted_text_qa.html", nextid=0):
    """
    Detailed view of an ExtractedText object, where the user can approve the
    record, edit its ExtractedComposition objects, skip to the next ExtractedText
    in the QA group, or exit to the index page.
    This view processes objects of different models with different QA workflows.
    The qa_focus variable is used to indicate whether an ExtractedText object is
    part of a QA Group, as with Composition records, or if the DataDocument/ExtractedText
    is its own QA Group, as with ExtractedCPCat and ExtractedHHDoc records.
    """
    extext = get_object_or_404(ExtractedText.objects.select_subclasses(), pk=pk)
    MANUAL_SCRIPT_ID = (
        Script.objects.filter(title="Manual (dummy)", script_type="EX").first().id
    )

    doc = DataDocument.objects.get(pk=pk)
    exscript = extext.extraction_script
    stats = ""
    qa_focus = "script"
    if extext.group_type in ["CP"]:
        qa_focus = "doc"
        #
        # Document-focused QA process
        #
        # If the object is an ExtractedCPCat record, there will be no Script
        # associated with it and no QA Group
        flagged_qs = extext.prep_cp_for_qa()
    elif extext.group_type in ["HH"]:
        pass
    else:
        qa_focus = "script"
        #
        # Extraction Script-focused QA process
        #
        # when not coming from extraction_script page, the document's script might not have
        # a QA Group yet.
        if not extext.qa_group:
            # create the qa group with the optional ExtractedText pk argument
            # so that the ExtractedText gets added to the QA group even if the
            # group uses a random sample
            qa_group = exscript.add_to_qa_group(pk)
            exscript.qa_begun = True
            exscript.save()
            extext.qa_group = qa_group
            extext.save()
        # get the next unapproved Extracted Text object
        # Its ID will populate the URL for the "Skip" button
        if extext.qa_checked:  # if ExtractedText object's QA process done, use 0
            nextid = 0
        else:
            nextid = extext.next_extracted_text_in_qa_group()
        # derive number of approved records and remaining unapproved in QA Group
        a = extext.get_approved_doc_count()
        r = extext.get_qa_queryset().count() - a
        stats = "%s document(s) approved, %s documents remaining" % (a, r)

    # If the Referer is set but not the extractionscript or a previous extracted text page
    # then when they hit the exit button send them back to their referer
    referer = request.headers.get("Referer", "")
    if "extractionscript" in referer or "extractedtext" in referer or referer == "":
        referer = "qa_extraction_script"
    # assign the destination link for the Exit button
    if extext.group_type in ["CO"] and extext.extraction_script_id == MANUAL_SCRIPT_ID:
        exit_url = reverse(
            "qa_manual_composition_script", kwargs={"pk": doc.data_group_id}
        )
    elif extext.group_type in ["CP"]:
        exit_url = reverse(
            "qa_chemical_presence_group", kwargs={"pk": doc.data_group_id}
        )
    else:
        exit_url = reverse(
            "qa_extraction_script", kwargs={"pk": extext.extraction_script_id}
        )

    # Create the formset factory for the extracted records
    # The model used for the formset depends on whether the
    # extracted text object matches a data document()
    # The QA view should exclude certain fields.
    ParentForm, ChildForm = create_detail_formset(
        doc,
        settings.EXTRA,
        can_delete=True,
        exclude=["weight_fraction_type", "true_cas", "true_chemname", "sid"],
    )

    if qa_focus == "script":
        if extext.data_document.data_group.is_functional_use:
            flagged_qs = extext.prep_functional_use_for_qa()
        else:
            detail_formset = ChildForm(instance=extext)
            flagged_qs = detail_formset.get_queryset()
    ext_form = ParentForm(instance=extext)
    extext.chemical_count = RawChem.objects.filter(extracted_text=extext).count()

    note, _ = QANotes.objects.get_or_create(extracted_text=extext)
    notesform = QANotesForm(instance=note)

    # Allow the user to edit the data document type
    document_type_form = DocumentTypeForm(None, instance=doc)
    document_type_form.fields[
        "document_type"
    ].queryset = DocumentType.objects.compatible(doc)
    document_type_form.fields["document_type"].label = "Data Document Type:"
    context = {
        "extracted_text": extext,
        "doc": doc,
        "script": exscript,
        "stats": stats,
        "nextid": nextid,
        "notesform": notesform,
        "ext_form": ext_form,
        "referer": referer,
        "document_type_form": document_type_form,
        "unsaved": "false",
        "exit_url": exit_url,
        "cards": cards_detail(request, doc, flagged_qs, False).content.decode("utf8"),
    }

    return render(request, template_name, context)


@login_required()
def save_qa_notes(request, pk):
    """
    This is an endpoint that serves the AJAX call
    """
    if request.method == "POST":
        qa_note_text = request.POST.get("qa_note_text")

        response_data = {}

        et = ExtractedText.objects.get(pk=pk)
        qa, created = QANotes.objects.get_or_create(extracted_text=et)
        qa.qa_notes = qa_note_text
        qa.save()

        response_data["result"] = "QA Note edits successfully saved"
        response_data["qa_note_text"] = qa.qa_notes

        return HttpResponse(json.dumps(response_data), content_type="application/json")
    else:
        return HttpResponse(
            json.dumps({"not a POST request": "this will not happen"}),
            content_type="application/json",
        )


@login_required()
def edit_qa_summary_note(request, model, pk):
    """
    This is an endpoint that serves the AJAX call
    """
    if request.method == "POST":
        qa_summary_note = request.POST.get("qa_summary_note")
        response_data = {}
        if model == "datagroup":
            instance = DataGroup.objects.get(pk=pk)
        elif model == "script":
            instance = Script.objects.get(pk=pk)
        else:
            instance = None

        if instance is None:
            return HttpResponse(
                json.dumps(
                    {
                        "result": "Error: model is invalid. Model must be in [datagroup, script]"
                    }
                ),
                status=400,
                content_type="application/json",
            )
        else:
            instance.qa_summary_note = qa_summary_note
            instance.save()
            response_data["result"] = "QA Summary Note saved successfully"

        return HttpResponse(json.dumps(response_data), content_type="application/json")
    else:
        return HttpResponse(
            json.dumps({"result": "Error: request method must be POST"}),
            status=400,
            content_type="application/json",
        )


@shared_task(bind=True, track_started=True, base=UserTask)
@usertask
def delete_extracted_script_task(self, pk):
    extraction_script = Script.objects.get(pk=pk)
    with transaction.atomic():
        ExtractedText.objects.filter(extraction_script=extraction_script).delete()
        QAGroup.objects.filter(extraction_script=extraction_script).delete()
        extraction_script.qa_begun = False
        extraction_script.save()

    return "task done"


@login_required()
def delete_extracted_text(
    request, pk, template_name="extraction_script/delete_progress.html"
):
    """
    This is an endpoint that deletes ExtractedText objected associated with the provided Script pk
    It performs the following actions:
        a. delete all extracted text associated with the extraction script
            (e.g. the extracted text for the document and the raw chem record)
        b. if any raw chem records have been associated with dsstox records,
            the linkage to the dsstoxsubstance table must be removed and the rid must be deleted
        c. reset the QA status of the extraction script to 'QA not begun'
        d. delete the QA group associated with the extraction script
        e. redirect the browser to the page from which the delete was called

    """
    script = get_object_or_404(Script, pk=pk)

    previous_url = request.META.get("HTTP_REFERER")
    if previous_url is not None and previous_url.endswith("extractionscripts/delete/"):
        redirect_to = "extraction_script_delete_list"
    else:
        redirect_to = "qa_extractionscript_index"

    # schedule async task as it may take sometime to finish the bulk deletion
    delete_task = delete_extracted_script_task.apply_async(
        args=[pk], shadow=f"extracted_script_delete.{pk}"
    )

    return render(
        request,
        template_name,
        {"script": script, "task": delete_task, "redirect_to": reverse(redirect_to)},
    )


@login_required()
def approve_extracted_text(request, pk):
    """
    This is an endpoint that processes the ExtractedText approval
    """
    extext = get_object_or_404(ExtractedText.objects.select_subclasses(), pk=pk)
    nextpk = extext.next_extracted_text_in_qa_group()

    if request.method == "POST":
        if extext.is_approvable():
            extext.qa_approved_date = timezone.now()
            extext.qa_approved_by = request.user
            extext.qa_checked = True
            extext.save()
            # The ExtractedText record is now approved.
            # Redirect to the appropriate page.

            referer = request.POST.get("referer", "")
            if referer == "data_document":
                # The user got to the QA page from a data document detail page,
                # so return there
                redirect_to = reverse(referer, kwargs={"pk": pk})
            elif not nextpk == 0:
                redirect_to = reverse("extracted_text_qa", args=[(nextpk)])
            elif nextpk == 0:
                # return to the top of the most local QA stack.
                # that may be the list of ExtractionScripts or
                # the list of Chemical Presence Data Groups
                redirect_to = extext.get_qa_index_path()

            messages.success(request, "The extracted text has been approved!")
            if is_safe_url(url=redirect_to, allowed_hosts=request.get_host()):
                return HttpResponseRedirect(redirect_to)
            else:
                return HttpResponseRedirect(reverse("extracted_text_qa", args=[(pk)]))
        else:
            # The ExtractedText record cannot be approved.
            # Return to the QA page and display an error.
            messages.error(
                request,
                "The extracted text \
                could not be approved. Make sure that if the records have been edited,\
                the QA Notes have been populated.",
            )
            return HttpResponseRedirect(reverse("extracted_text_qa", args=[(pk)]))
