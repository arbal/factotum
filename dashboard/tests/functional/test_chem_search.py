from django.test import TestCase, override_settings
from django.test.client import Client
from django.urls import resolve
from django.contrib.auth.models import User
from haystack.management.commands import update_index, clear_index
from haystack import connections
import time
from django.conf import settings
from dashboard.models import DSSToxSubstance
from lxml import html



@override_settings(HAYSTACK_CONN='test_index')
class ChemSearchTest(TestCase):
    fixtures = ['00_superuser.yaml', '01_lookups.yaml',
                '02_datasource.yaml', '03_datagroup.yaml', '04_PUC.yaml',
                '05_product.yaml', '06_datadocument.yaml', '07_script.yaml',
                '08_extractedtext.yaml', '09_productdocument.yaml', '10_extractedchemical', '11_dsstoxsubstance']

    def setUp(self):
        print('Test case setUp() method running')
        self.c = Client()
        index_start = time.time()
        update_index.Command().handle( remove=True, using=['test_index'], interactive=False)
        index_elapsed = time.time() - index_start
        print('Indexing took %s seconds' % index_elapsed)

    def tearDown(self):
        clear_index.Command().handle( using=['test_index'], interactive=False)

    def test_chem_search(self):
        response = self.c.get('/chem_search/?chemical=dibutyl')
        #print(response.content)
        self.assertContains(response, '"matchedDataDocuments": 1')
        self.assertContains(response, '"probableDataDocumentMatches": 55')
        self.assertNotContains(response, 'Sun_INDS_89')

        response = self.c.get('/chem_search/?chemical=ethylparaben')
        self.assertContains(response, 'SPICEBOMB3PCSGS')
        self.assertContains(response, 'The Healing Garden')
    
    def test_chemical_search_ui_results(self):
        response = self.client.get('/findchemical/?q=ethyl').content.decode('utf8')
        response_html = html.fromstring(response)
        print(response_html.xpath('string(/html/body/div[1]/div/div[2]/ol)'))
        self.assertIn('Sun_INDS_89',
                      response_html.xpath('string(/html/body/div[1]/div/div[2]/ol)'),
                      'The link to Sun_INDS_89 must be returned by a chemical search for "ethyl"')

