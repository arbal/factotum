from django.contrib.auth.models import User
from dashboard.models import DataGroup, DataDocument, GroupType, DocumentType
from django.test import RequestFactory, TestCase, Client
from dashboard.tests.loader import load_model_objects
from django.core.exceptions import ValidationError
from django.urls import resolve

import os
import io
from dashboard import views
from django.core.files.uploadedfile import (InMemoryUploadedFile,
                                            TemporaryUploadedFile)
from dashboard.tests.loader import fixtures_standard



class DDTestModel(TestCase):

    fixtures = fixtures_standard

    def setUp(self):
        self.client = Client()

    def test_dd_model_with_wrong_document_type(self):
        # Choose a Composition group
        dgcomp = DataGroup.objects.filter(group_type__title='Composition').first()
        # Choose a document type from the wrong parent group type
        dt_fu = DocumentType.objects.filter(group_type__title='Functional use').first()
        dd = DataDocument.objects.create(filename="some.pdf", title="My Document", document_type = dt_fu , data_group=dgcomp)
        with self.assertRaises(ValidationError):
            dd.save()
            dd.full_clean()
        dt_comp = DocumentType.objects.filter(group_type__title='Composition').first()
        dd = DataDocument.objects.create(filename="some.pdf", title="My Document", document_type = dt_comp , data_group=dgcomp)
        dd.save()
        self.assertEqual(dt_comp.title, dd.document_type.title )

class DDTestUpload(TestCase):

    fixtures = fixtures_standard

    def setUp(self):
        self.factory = RequestFactory()
        self.client.login(username='Karyn', password='specialP@55word')

    def testGoodGroupTypeInCSV(self):
        csv_string_good = ("filename,title,document_type,url,organization\n"
                "0bf5755e-3a08-4024-9d2f-0ea155a9bd17.pdf,NUTRA NAIL,MS,, \n"
                "0c68ab16-2065-4d9b-a8f2-e428eb192465.pdf,Body Cream,MS,, \n")
                # DocumentType.objects.all().filter(group_type__title='Composition').values('id', 'title')
                # assigning the (compatible) MSDS document type in the csv

        data = io.StringIO(csv_string_good)
        csv_len = len(csv_string_good)

        sample_csv = InMemoryUploadedFile(data,
                                            field_name='csv',
                                            name='register_records.csv',
                                            content_type='text/csv',
                                            size=csv_len,
                                            charset='utf-8')
        form_data= {'name': ['Composition Type Group'],
                    'description': ['test data group'],
                    'group_type': ['2'], # Composition
                    'downloaded_by': ['1'],
                    'downloaded_at': ['08/02/2018'],
                    'download_script': ['1'],
                    'data_source': ['10']}
        request = self.factory.post(path='/datagroup/new', data=form_data)
        request.FILES['csv'] = sample_csv
        request.user = User.objects.get(username='Karyn')
        request.session={}
        request.session['datasource_title'] = 'Walmart'
        request.session['datasource_pk'] = 10
        resp = views.data_group_create(pk = 10, request=request)
        self.assertEqual(resp.status_code,302,
                        "Should be redirected to new datagroup detail page")
        # does the datagroup in the ORM contain the new data docs?
        newdg_pk = resolve(resp.url).kwargs['pk']
        newdg = DataGroup.objects.get(pk=newdg_pk)
        newdds = DataDocument.objects.filter(data_group=newdg)
        self.assertEqual(newdds.count(),2,'There should be two new data documents')

    def testBadGroupTypeInCSV(self):
        csv_string_bad = ("filename,title,document_type,url,organization\n"
                "0bf5755e-3a08-4024-9d2f-0ea155a9bd17.pdf,NUTRA NAIL,9,, \n"
                "0c68ab16-2065-4d9b-a8f2-e428eb192465.pdf,Body Cream,4,, \n")
                # DocumentType.objects.all().exclude(group_type__title='Composition').values('id', 'title')
                # assigning the (incompatible) *chemical use disclosure* document type in row 1 of the csv

        data = io.StringIO(csv_string_bad)
        csv_len = len(csv_string_bad)

        sample_csv = InMemoryUploadedFile(data,
                                            field_name='csv',
                                            name='register_records.csv',
                                            content_type='text/csv',
                                            size=csv_len,
                                            charset='utf-8')
        form_data= {'name': ['Composition Type Group'],
                    'description': ['test data group'],
                    'group_type': ['2'], # Composition
                    'downloaded_by': ['1'],
                    'downloaded_at': ['08/02/2018'],
                    'download_script': ['1'],
                    'data_source': ['10']}
        request = self.factory.post(path='/datagroup/new', data=form_data)
        request.FILES['csv'] = sample_csv
        request.user = User.objects.get(username='Karyn')
        request.session={}
        request.session['datasource_title'] = 'Walmart'
        request.session['datasource_pk'] = 10
        resp = views.data_group_create(pk = 10 , request=request)
        # the upload form should be invalid
        self.assertIn('CSV has bad data in row/s:'.encode(), resp.content)
