import csv
import datetime
from django.db.models import Value, IntegerField
from django.shortcuts import render, reverse, redirect
from django.contrib.auth.decorators import login_required
from django.http import StreamingHttpResponse

from dashboard.models import RawChem, DSSToxLookup, DataGroup, DataDocument
from dashboard.forms import DataGroupSelector
from dashboard.utils import get_extracted_models


@login_required()
def chemical_curation_index(
    request, template_name="chemical_curation/chemical_curation_index.html"
):
    uncurated_chemical_count = RawChem.objects.filter(dsstox_id=None).count()
    records_processed = 0

    dg_picker_form = DataGroupSelector()

    data = {
        "dg_picker_form": dg_picker_form,
        "uncurated_chemical_count": uncurated_chemical_count,
        "records_processed": records_processed,
    }

    if "POST" == request.method:
        try:
            csv_file = request.FILES["csv_file"]
            info = [x.decode("ascii", "ignore") for x in csv_file.readlines()]
            records_processed = len(info) - 1
            table = csv.DictReader(info)

            missing = list(
                set(["external_id", "rid", "sid", "true_chemical_name", "true_cas"])
                - set(table.fieldnames)
            )
            if missing:
                data.update(
                    {
                        "error_message": "File must be a CSV file with the following rows:"
                        " external_id, rid, sid, true_chemical_name, true_cas"
                    }
                )
                return render(request, template_name, data)

            # if file is too large, return
            if csv_file.multiple_chunks():
                error = "Uploaded file is too big (%.2f MB)." % (
                    csv_file.size / (1000 * 1000)
                )
                data.update({"error_message": error})
                return render(request, template_name, data)

            for i, row in enumerate(table):
                try:
                    if DSSToxLookup.objects.filter(sid=row["sid"]).exists():
                        DSSToxLookup.objects.filter(sid=row["sid"]).update(
                            true_cas=row["true_cas"],
                            true_chemname=row["true_chemical_name"],
                        )
                    else:
                        chem = DSSToxLookup.objects.create(
                            true_cas=row["true_cas"],
                            true_chemname=row["true_chemical_name"],
                            sid=row["sid"],
                        )
                        chem.save()
                    sid = DSSToxLookup.objects.filter(sid=row["sid"]).first()
                    RawChem.objects.filter(id=row["external_id"]).update(
                        rid=row["rid"], dsstox_id=sid.id
                    )
                except Exception as e:
                    print(e)
                    pass

        except Exception as e:
            # This is the catchall - MySQL database has went away, etc....
            error = "Something is seriously wrong with this csv - %s" % repr(e)
            data.update({"error_messasage": error})
            return render(request, template_name, data)
    if records_processed > 0:
        data.update({"records_processed": records_processed})
    return render(request, template_name, data)


#
# Downloading uncurated raw chemical records by Data Group
#
# This clever way to combine writing the headers
# with writing the rows, including the "yield" keyword, is from
# https://stackoverflow.com/questions/45578196/adding-rows-manually-to-streaminghttpresponse-django


class Echo:
    """An object that implements just the write method of the file-like
    interface.
    """

    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value


def iterate_rawchems(rows, pseudo_buffer):
    writer = csv.writer(pseudo_buffer)
    yield pseudo_buffer.write("id,raw_cas,raw_chem_name,rid,datagroup_id\n")
    for row in rows:
        yield writer.writerow(
            [
                row["id"],
                row["raw_cas"],
                row["raw_chem_name"],
                row["rid"] if row["rid"] else "",
                row["dg_id"],
            ]
        )


@login_required()
def download_raw_chems_dg(request, pk):
    dg = DataGroup.objects.get(pk=pk)

    # Limit the response to 10,000 records
    uncurated_chems = (
        RawChem.objects.filter(dsstox_id=None)
        .filter(extracted_text__data_document__data_group=dg)
        .annotate(dg_id=Value(pk, IntegerField()))
        .values("id", "raw_cas", "raw_chem_name", "rid", "dg_id")[0:10000]
    )
    pseudo_buffer = Echo()
    response = StreamingHttpResponse(
        streaming_content=(iterate_rawchems(uncurated_chems, pseudo_buffer)),
        content_type="text/csv",
    )

    response["Content-Disposition"] = (
        'attachment; filename="uncurated_chemicals_%s_%s.csv"'
        % (pk, datetime.datetime.now().strftime("%Y%m%d"))
    )
    return response


@login_required()
def chemical_delete(request, doc_pk, chem_pk):
    doc = DataDocument.objects.get(pk=doc_pk)
    _, Chemical = get_extracted_models(doc.data_group.group_type.code)
    chem = Chemical.objects.get(pk=chem_pk)
    chem.delete()
    return redirect(doc)
