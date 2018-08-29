from django.urls import resolve
from django.test import RequestFactory, TestCase, Client
from django.http import HttpRequest
from dashboard import views
from dashboard.models import *
from django.core.files.uploadedfile import InMemoryUploadedFile, SimpleUploadedFile
import tempfile, csv, os, io
from django.contrib.auth.models import User



class UploadExtractedFileTest(TestCase):
    fixtures = ['00_superuser.yaml', '01_lookups.yaml',
                '02_datasource.yaml', '03_datagroup.yaml', '04_PUC.yaml',
                '05_product.yaml', '06_datadocument.yaml', '07_script.yaml',
                '08_extractedtext.yaml', '09_productdocument.yaml', '10_extractedchemical', '11_dsstoxsubstance']

    def setUp(self):
        self.c = Client()
        self.factory = RequestFactory()
        self.c.login(username='Karyn', password='specialP@55word')


    def generate_valid_chem_csv_string(self):
        csv_string = ("data_document_id,data_document_filename,"
                    "prod_name,doc_date,rev_num,raw_category,raw_cas,raw_chem_name,"
                    "report_funcuse,raw_min_comp,raw_max_comp,unit_type,"
                    "ingredient_rank,raw_central_comp"
                    "\n"
                    "8,11177849.pdf,Alberto European Hairspray (Aerosol) - All Variants,,,aerosol hairspray,"
                    "0000075-37-6,hydrofluorocarbon 152a (difluoroethane),,0.39,0.42,1,,"
                    "\n"
                    "7,11165872.pdf,Alberto European Hairspray (Aerosol) - All Variants,,,aerosol hairspray,"
                    "0000064-17-5,sd alcohol 40-b (ethanol),,0.5,0.55,1,,"
                    )
        return csv_string
    

    def generate_chem_csv(self):
        try:
            myfile = open('British_Petroleum_(Air)_1_extract_template.csv', 'w')
            wr = csv.writer(myfile)
            wr.writerow(("data_document_id,data_document_filename,"
                        "prod_name,doc_date,rev_num,raw_category,raw_cas,raw_chem_name,"
                        "report_funcuse,raw_min_comp,raw_max_comp,unit_type,"
                        "ingredient_rank,raw_central_comp"))
            wr.writerow(("8,11177849.pdf,Alberto European Hairspray (Aerosol) - All Variants,,,aerosol hairspray,"
                        "0000075-37-6,hydrofluorocarbon 152a (difluoroethane),,0.39,0.42,1,,"))
            wr.writerow(("7,11165872.pdf,Alberto European Hairspray (Aerosol) - All Variants,,,aerosol hairspray,"
                        "0000064-17-5,sd alcohol 40-b (ethanol),,0.5,0.55,1,,"))
        finally:
            myfile.close()
        return myfile


    def test_chem_upload(self):
        sample_csv = self.generate_valid_chem_csv_string()
        sample_csv_bytes = sample_csv.encode(encoding='UTF-8',errors='strict' )
        in_mem_sample_csv = InMemoryUploadedFile(
                io.BytesIO(sample_csv_bytes),
                field_name='extract_file',
                name='British_Petroleum_(Air)_1_extract_template.csv',
                content_type='text/csv',
                size=len(sample_csv),
                charset='utf-8',
        )
        req_data = {'script_selection': 5, 
                    'weight_fraction_type': 1, 
                    'extract_button': 'Submit', 
                    }

        req = self.factory.post(path = '/datagroup/6/' , data=req_data)
        req.FILES['extract_file'] = in_mem_sample_csv
        req.user = User.objects.get(username='Karyn')
        # Now get the response
        resp = views.data_group_detail(request=req, pk=6)
        self.assertContains(resp,'2 extracted records uploaded successfully.')

        doc_count = DataDocument.objects.filter(raw_category='aerosol hairspray').count()
        self.assertTrue(doc_count > 0, 'DataDocument raw category values must be updated.')