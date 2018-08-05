from django.test import TestCase
from django.test.client import Client
from django.urls import resolve
from django.contrib.auth.models import User


class ChemSearchTest(TestCase):
    fixtures = ['00_superuser.yaml', '01_lookups.yaml',
                '02_datasource.yaml', '03_datagroup.yaml', '04_PUC.yaml',
                '05_product.yaml', '06_datadocument.yaml', '07_script.yaml',
                '08_extractedtext.yaml', '09_productdocument.yaml', '10_extractedchemical', '11_dsstoxsubstance']

    def setUp(self):
        self.c = Client()

    def test_chem_search(self):
        response = self.c.get('/chem_search/?chemical=dibutyl')
        self.assertContains(response, '"matchedDataDocuments": 1')
        self.assertContains(response, '"probableDataDocumentMatches": 2')
        self.assertNotContains(response, 'Sun_INDS_89')

        response = self.c.get('/chem_search/?chemical=ethylparaben')
        self.assertContains(response, 'Sun_INDS_89')
        self.assertContains(response, 'Avgas 100LL (<0.1% Benzene)')
        self.assertContains(response, 'Jet A')
