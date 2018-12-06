import tempfile, csv, os, io

from django.urls import resolve
from django.http import HttpRequest
from django.test import RequestFactory, TestCase, Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import InMemoryUploadedFile

from dashboard import views
from dashboard.models import *



class UploadExtractedFileTest(TestCase):
    fixtures = ['00_superuser.yaml', '01_lookups.yaml',
                '02_datasource.yaml', '03_datagroup.yaml', '04_PUC.yaml',
                '05_product.yaml', '06_datadocument.yaml', '07_script.yaml']

    def setUp(self):
        self.c = Client()
        self.factory = RequestFactory()
        self.c.login(username='Karyn', password='specialP@55word')


    def generate_valid_chem_csv(self):
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
        sample_csv_bytes = csv_string.encode(encoding='UTF-8',errors='strict' )
        in_mem_sample_csv = InMemoryUploadedFile(
                io.BytesIO(sample_csv_bytes),
                field_name='extract_file',
                name='British_Petroleum_(Air)_1_extract_template.csv',
                content_type='text/csv',
                size=len(csv_string),
                charset='utf-8')
        return in_mem_sample_csv

    def generate_invalid_chem_csv(self):
        csv_string = ("data_document_id,data_document_filename,"
                    "prod_name,doc_date,rev_num,raw_category,raw_cas,raw_chem_name,"
                    "report_funcuse,raw_min_comp,raw_max_comp,unit_type,"
                    "ingredient_rank,raw_central_comp"
                    "\n"
                    "8,11177849.pdf,Alberto European Hairspray (Aerosol) - All Variants,,,aerosol hairspray,"
                    "0000075-37-6,hydrofluorocarbon 152a (difluoroethane),,0.39,0.42,1,,"
                    "\n"
                    "8,11177849.pdf,A different prod_name with the same datadocument,,,aerosol hairspray,"
                    "0000064-17-5,sd alcohol 40-b (ethanol),,0.5,0.55,1,,"
                    )
        sample_csv_bytes = csv_string.encode(encoding='UTF-8',errors='strict' )
        in_mem_sample_csv = InMemoryUploadedFile(
                io.BytesIO(sample_csv_bytes),
                field_name='extract_file',
                name='British_Petroleum_(Air)_1_extract_template.csv',
                content_type='text/csv',
                size=len(csv_string),
                charset='utf-8')
        return in_mem_sample_csv

    def test_chem_upload(self):
        req_data = {'script_selection': 5,
                    'weight_fraction_type': 1,
                    'extract_button': 'Submit',
                    }

        req = self.factory.post(path = '/datagroup/6/' , data=req_data)
        req.user = User.objects.get(username='Karyn')
        req.FILES['extract_file'] = self.generate_invalid_chem_csv()
        # get error in response
        resp = views.data_group_detail(request=req, pk=6)
        # print(resp.content)
        self.assertContains(resp,'must be 1:1')
        text_count = ExtractedText.objects.all().count()
        self.assertTrue(text_count < 2, 
                                    'Shouldn\'t be 2 extracted texts uploaded')
        # Now get the success response
        req.FILES['extract_file'] = self.generate_valid_chem_csv()
        doc_count = DataDocument.objects.filter(
                                    raw_category='aerosol hairspray').count()
        self.assertTrue(doc_count == 0, 
                            'DataDocument raw category shouldn\'t exist yet.')
        resp = views.data_group_detail(request=req, pk=6)
        self.assertContains(resp,'2 extracted records uploaded successfully.')

        doc_count = DataDocument.objects.filter(
                                    raw_category='aerosol hairspray').count()
        self.assertTrue(doc_count > 0, 
                            'DataDocument raw category values must be updated.')
        text_count = ExtractedText.objects.all().count()
        self.assertTrue(text_count == 2, 'Should be 2 extracted texts')
        dg = DataGroup.objects.get(pk=6)
        dg.delete()

    def test_presence_upload(self):
        sample_csv = ("data_document_id,data_document_filename,"
                    "doc_date,raw_category,raw_cas,raw_chem_name,"
                    "cat_code,description_cpcat,cpcat_code,cpcat_sourcetype"
                    "\n"
                    "254780,11177849.pdf,,list presence category,"
                    "0000075-37-6,hydrofluorocarbon 152a,presence_cat_code,"
                    "desc,cpcat_code,free"
                    "\n"
                    "254781,11165872.pdf,,list presence category,"
                    "0000064-17-5,sd alcohol 40-b (ethanol),presence_cat_code,"
                    "desc,cpcat_code,free"
        )
        sample_csv_bytes = sample_csv.encode(encoding='UTF-8',errors='strict' )
        in_mem_sample_csv = InMemoryUploadedFile(
                io.BytesIO(sample_csv_bytes),
                field_name='extract_file',
                name='SIRI_Chemical_Presence_extract_template.csv',
                content_type='text/csv',
                size=len(sample_csv),
                charset='utf-8',
        )
        req_data = {'script_selection': 5,
                    'extract_button': 'Submit',
                    }

        req = self.factory.post('/datagroup/49/' , data=req_data)
        req.FILES['extract_file'] = in_mem_sample_csv
        req.user = User.objects.get(username='Karyn')
        self.assertEqual(len(ExtractedCPCat.objects.all()),0,
                            "Empty before upload.")
        # Now get the response
        resp = views.data_group_detail(request=req, pk=49)
        self.assertContains(resp,'2 extracted records uploaded successfully.')

        doc_count = DataDocument.objects.filter(raw_category='list presence category').count()
        self.assertTrue(doc_count > 0, 'DataDocument raw category values must be updated.')

        self.assertEqual(len(ExtractedCPCat.objects.all()),2,
                            "Two after upload.")

        dg = DataGroup.objects.get(pk=49)
        dg.delete()

    def test_functionaluse_upload(self):
        # This action is performed on a data document without extracted text
        # but with a matched data document. DataDocument 500 was added to the
        # seed data for this test
        dd_id = 500
        dd = DataDocument.objects.get(pk=dd_id)
        #et = ExtractedText.objects.get(data_document=dd)
        dd_pdf = dd.pdf_url()
        
        sample_csv = ("data_document_id,data_document_filename,prod_name,"
                      "doc_date,rev_num,raw_category,raw_cas,raw_chem_name,report_funcuse"
                    "\n"
                    "%s,"
                    "%s,"
                    "sample functional use product,"
                    "2018-04-07,"
                    ","
                    "raw PUC,"
                    "RAW-CAS-01,"
                    "raw chemname 01,"
                    "surfactant" % (dd_id, dd_pdf)
        )
        sample_csv_bytes = sample_csv.encode(encoding='UTF-8',errors='strict' )
        in_mem_sample_csv = InMemoryUploadedFile(
                io.BytesIO(sample_csv_bytes),
                field_name='extract_file',
                name='Functional_use_extract_template.csv',
                content_type='text/csv',
                size=len(sample_csv),
                charset='utf-8',
        )
        req_data = {'script_selection': 5,
                    'extract_button': 'Submit',
                    }
        
        req = self.factory.post('/datagroup/50/' , data=req_data)
        req.FILES['extract_file'] = in_mem_sample_csv
        req.user = User.objects.get(username='Karyn')
        self.assertEqual(len(ExtractedFunctionalUse.objects.filter(extracted_text_id=dd_id)),0,
                            "Empty before upload.")
        # Now get the response
        resp = views.data_group_detail(request=req, pk=50)
        self.assertContains(resp,'1 extracted records uploaded successfully.')

        doc_count = DataDocument.objects.filter(raw_category='raw PUC').count()
        self.assertTrue(doc_count > 0, 'DataDocument raw category values must be updated.')

        self.assertEqual(len(ExtractedFunctionalUse.objects.filter(extracted_text_id=dd_id)),1,
                            "One new ExtractedFunctionalUse after upload.")

        #dg = DataGroup.objects.get(pk=50)
        #dg.delete()
