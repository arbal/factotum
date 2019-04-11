from django.contrib.auth.decorators import login_required
from django.shortcuts import render, reverse
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib import messages
from dashboard.models import *
import datetime
import csv


@login_required()
def chemical_curation_index(request, template_name='chemical_curation/chemical_curation_index.html'):
    uncurated_chemical_count = RawChem.objects.filter(dsstox_id=None).count()
    records_processed = 0

    data = {'uncurated_chemical_count': uncurated_chemical_count, 'records_processed': records_processed}
    # if not GET, then proceed
    if "POST" == request.method:
        try:
            # if not a csv file
            csv_file = request.FILES["csv_file"]
            if not csv_file.name.endswith('.csv'):
                data.update({'error_message': 'File is not CSV type'})
                return render(request, template_name, data)
            # if file is too large, return
            if csv_file.multiple_chunks():
                error = "Uploaded file is too big (%.2f MB)." % (csv_file.size / (1000 * 1000))
                data.update({'error_message': error})
                return render(request, template_name, data)

            file_data = csv_file.read().decode("utf-8")
            lines = file_data.split("\n")

            # loop over the lines and save them in db. If error , store as string and then display
            records_processed = len(lines) - 1
            for line in lines:
                fields = line.split(",")
                data_dict = {}
                data_dict["raw_chemical_id"] = fields[0].strip()
                data_dict["rid"] = fields[1].strip()
                data_dict["sid"] = fields[2].strip()
                data_dict["true_chemical_name"] = fields[3].strip()
                data_dict["true_cas"] = fields[4].strip()
                # If it is the header row check to see that the columns are in order.
                if data_dict["raw_chemical_id"] == "external_id":
                    if (data_dict["raw_chemical_id"] != "external_id") or (data_dict['sid'] != 'sid') or \
                            (data_dict['true_chemical_name'] != "true_chemical_name") or \
                            (data_dict['true_cas'] != 'true_cas'):
                        data.update({"error_message": "Check to ensure your column headers are in order."})
                        return render(request, template_name, data)
                else:
                    try:
                        # Check to see of SID exists,
                        if DSSToxLookup.objects.filter(sid=data_dict['sid']).exists():
                            # if is does exist Overwrite the existing True CAS and Chemname
                            DSSToxLookup.objects.filter(sid=data_dict['sid']). \
                                update(true_cas=data_dict["true_cas"],
                                       true_chemname=data_dict["true_chemical_name"])
                        # if not create it in DSSToxLookup
                        else:
                            chem = DSSToxLookup.objects.create(true_cas=data_dict["true_cas"],
                                                               true_chemname=data_dict["true_chemical_name"],
                                                               sid=data_dict["sid"])
                            chem.save()
                        # ensure link back to DSSToxLookup
                        sid_id = DSSToxLookup.objects.filter(sid=data_dict['sid'])
                        RawChem.objects.filter(id=data_dict["raw_chemical_id"]).update(rid=data_dict['rid'],
                                                                                       dsstox_id=sid_id[0].id)
                    except Exception as e:
                        print(e)
                        pass

        except Exception as e:
            # This is the catchall - MySQL database has went away, etc....
            error = "Something is seriously wrong with this csv - %s" % repr(e)
            data.update({"error_messasage": error})
            return render(request, template_name, data)
            messages.error(request, "Unable to upload file. " + repr(e))
    if records_processed > 0:
        data.update({"records_processed": records_processed})
    return render(request, template_name, data)


@login_required()
def download_raw_chems(stats):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="uncurated_chemicals_%s.csv"' % \
                                      (datetime.datetime.now().strftime("%Y%m%d"))

    writer = csv.writer(response)
    writer.writerow(['dashboard_rawchem_id', 'raw_cas', 'raw_chem_name', 'rid'])
    for rawchem in RawChem.objects.filter(dsstox_id=None):
        writer.writerow([rawchem.id, rawchem.raw_cas, rawchem.raw_chem_name, rawchem.rid if rawchem.rid else ''])
    return response
