from django.test import TestCase
from django.test.client import Client
from lxml import html

from django.urls import resolve
from django.contrib.auth.models import User

class FacetedSearchTest(TestCase):
    fixtures = ['00_superuser.yaml', '01_lookups.yaml',
                '02_datasource.yaml', '03_datagroup.yaml', '04_PUC.yaml',
                '05_product.yaml', '06_datadocument.yaml', '07_script.yaml',
                '08_extractedtext.yaml', '09_productdocument.yaml', '10_extractedchemical', '11_dsstoxsubstance']
    def setUp(self):
        self.c = Client()

    def test_faceted_search_excludes_chemicals(self):
        response = self.c.get('/find/?q=ethyl')
        self.assertContains(response, 'Data Document')
        self.assertNotContains(response, 'Extracted Chemical')
        self.assertNotContains(response, 'DSSTox Substance')

    def test_chemical_search_ui_results(self):
        response = self.client.get('/findchemical/?q=ethyl').content.decode('utf8')
        response_html = html.fromstring(response)
        self.assertIn('Sun_INDS_89',
                      response_html.xpath('string(/html/body/div[1]/div/div[2]/ol/li[1]/a[@href="/datadocument/156051"])'),
                      'The link to Sun_INDS_89 must be returned by a chemical search for "ethyl"')

