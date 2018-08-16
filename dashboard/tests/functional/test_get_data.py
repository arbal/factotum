from django.urls import resolve
from django.test import TestCase
from django.test.client import Client

from dashboard import views

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from dashboard.views.get_data import * 

class TestGetData(TestCase):
    fixtures = ['00_superuser.yaml', '01_lookups.yaml',
                '02_datasource.yaml', '03_datagroup.yaml', '04_PUC.yaml',
                '05_product.yaml', '06_datadocument.yaml','07_script.yaml',
                '08_extractedtext.yaml', '09_productdocument.yaml', '10_extractedchemical', '11_dsstoxsubstance']

    def setUp(self):
        self.client = Client()

    def test_dtxsid_stats(self):
        ids =["DTXSID9022528", "DTXSID1020273","DTXSID6026296","DTXSID2021781"]
        #stats = stats_by_dtxsids(ids)
        #print(stats)
        #csv_out = download_chem_stats(stats)
        #print(csv_out.content)
        print("This test needs to be updated")




