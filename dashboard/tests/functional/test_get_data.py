from django.urls import resolve
from django.test import TestCase
from django.test.client import Client

from dashboard import views

from django.contrib.auth import authenticate
from django.contrib.auth.models import User

class TestGetData(TestCase):
    fixtures = ['00_superuser.yaml', '01_lookups.yaml',
                '02_datasource.yaml', '03_datagroup.yaml', '04_PUC.yaml',
                '05_product.yaml', '06_datadocument.yaml','07_script.yaml',
                '08_extractedtext.yaml', '09_productdocument.yaml', '10_extractedchemical', '11_dsstoxsubstance']

    def setUp(self):
        self.client = Client()
    
    def test_no_auth(self):
        # the Get Data menu item should be available to a user who isn't logged in
        response = self.client.get('/')
        self.assertContains(response, 'Get Data')
        response = self.client.get('/get_data/')
        self.assertContains(response, 'Summary metrics by chemical')



