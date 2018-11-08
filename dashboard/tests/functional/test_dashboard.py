import csv
import time
from lxml import html

from django.urls import resolve
from django.test import TestCase

from dashboard.tests.loader import load_model_objects
from dashboard import views
from dashboard.models import *

class DashboardTest(TestCase):

    def setUp(self):
        self.objects = load_model_objects()
        # self.test_start = time.time()

    # def tearDown(self):
    #     self.test_elapsed = time.time() - self.test_start
    #     print('\nFinished with ' + self._testMethodName + ' in {:.2f}s'.format(self.test_elapsed))

    def test_public_navbar(self):
        self.client.logout()
        response = self.client.get('/').content.decode('utf8')
        response_html = html.fromstring(response)
        self.assertIn('factotum', response_html.xpath('string(/html/body/nav//a[@href="/"]/text())'),
                         'The app name factotum should appear in the public navbar')
        self.assertNotIn('QA', response_html.xpath('string(/html/body/nav//a[@href="/qa/"])'),
                         'The link to /qa/ should not appear in the public navbar')

    def test_logged_in_navbar(self):
        self.client.login(username='Karyn', password='specialP@55word')
        response = self.client.get('/').content.decode('utf8')
        response_html = html.fromstring(response)
        self.assertIn('QA', response_html.xpath('string(/html/body/nav//a[@href="/qa/"])'),
                      'The link to /qa/ must be in the logged-in navbar')

        found = resolve('/qa/')
        self.assertEqual(found.func, views.qa_index)

    def test_percent_extracted_text_doc(self):
        response = self.client.get('/').content.decode('utf8')
        response_html = html.fromstring(response)
        extracted_doc_count = response_html.xpath('/html/body/div[1]/div[1]/div[4]/div/div')[0].text
        self.assertEqual('0%', extracted_doc_count)

        self.objects.doc.extracted = True
        self.objects.doc.save()
        response = self.client.get('/').content.decode('utf8')
        response_html = html.fromstring(response)
        extracted_doc_count = response_html.xpath('/html/body/div[1]/div[1]/div[4]/div/div')[0].text
        self.assertEqual('100%', extracted_doc_count)

    def test_PUC_download(self):
        p = self.objects.puc
        puc_line = (p.gen_cat+','+p.prod_fam+','+p.prod_type+','+p.description+','+str(p.get_level())+','+str(p.producttopuc_set.count()))
        # get csv
        response = self.client.get('/dl_pucs/')
        self.assertEqual(response.status_code, 200)
        csv_lines = response.content.decode('ascii').split('\r\n')
        # check header
        self.assertEqual(csv_lines[0],'gen_cat,prod_fam,prod_type,description,PUC_type,num_prods')
        # check the PUC from loader
        self.assertEqual(csv_lines[1],puc_line)

    def test_chem_search_input(self):
        self.client.logout()
        response = self.client.get('/').content.decode('utf8')
        response_html = html.fromstring(response)
        self.assertTrue(response_html.xpath('//*[@id="chemical_search"]'),
                      'The chemical search input should appear on the dashboard')

    def test_chemical_card(self): #this can be joined w/ the one being merged in
        response = self.client.get('/').content.decode('utf8')
        self.assertIn('DSS Tox Chemicals', response,
                                    'Where is the DSS Tox Chemicals card???')
        response_html = html.fromstring(response)
        num_dss = int(response_html.xpath('//*[@name="dsstox"]')[0].text)
        self.assertEqual(num_dss, 1, 'There should be one DSSToxSubstance')
