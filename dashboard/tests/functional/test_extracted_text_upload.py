import tempfile, csv, os, io

from django.urls import resolve
from django.http import HttpRequest
from django.test import RequestFactory, TestCase, Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import InMemoryUploadedFile

from dashboard import views
from dashboard.models import *
from dashboard.tests.loader import fixtures_standard

def make_upload_csv(filename):
    with open(filename) as f:
        sample_csv = ''.join([line for line in f.readlines()])
    sample_csv_bytes = sample_csv.encode(encoding='UTF-8',errors='strict' )
    in_mem_sample_csv = InMemoryUploadedFile(
            file=io.BytesIO(sample_csv_bytes),
            field_name='extract_file',
            name='test.csv',
            content_type='text/csv',
            size=len(sample_csv),
            charset='utf-8',
    )
    return in_mem_sample_csv


class UploadExtractedFileTest(TestCase):
    fixtures = ['00_superuser.yaml', '01_lookups.yaml',
                '02_datasource.yaml', '03_datagroup.yaml', '04_PUC.yaml',
                '05_product.yaml', '06_datadocument.yaml', '08_script.yaml']

            

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
        print(text_count)
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
        # Delete the CPCat records that were loaded with the fixtures
        ExtractedCPCat.objects.all().delete()
        self.assertEqual(len(ExtractedCPCat.objects.all()),0,
                        "Should be empty before upload.")
        usr = User.objects.get(username='Karyn')
        # test for error to be propogated w/o a 1:1 match of ExtCPCat to DataDoc
        in_mem_sample_csv = make_upload_csv('sample_files/presence_cpcat.csv')
        req_data = {'script_selection': 5,
                    'extract_button': 'Submit',
                    }
        req = self.factory.post('/datagroup/49/' , data=req_data)
        req.FILES['extract_file'] = in_mem_sample_csv
        req.user = usr
        resp = views.data_group_detail(request=req, pk=49)
        self.assertContains(resp,'must be 1:1')
        self.assertEqual(len(ExtractedCPCat.objects.all()),0,
                        "ExtractedCPCat records remain 0 if error in upload.")
        # test for error to propogate w/ too many chars in a field
        in_mem_sample_csv = make_upload_csv('sample_files/presence_chars.csv')
        req.FILES['extract_file'] = in_mem_sample_csv
        resp = views.data_group_detail(request=req, pk=49)
        self.assertContains(resp,'Ensure this value has at most 50 characters')
        self.assertEqual(len(ExtractedCPCat.objects.all()),0,
                        "ExtractedCPCat records remain 0 if error in upload.")
        # test that upload works successfully...
        in_mem_sample_csv = make_upload_csv('sample_files/presence_good.csv')
        req.FILES['extract_file'] = in_mem_sample_csv
        resp = views.data_group_detail(request=req, pk=49)
        self.assertContains(resp,'3 extracted records uploaded successfully.')

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
