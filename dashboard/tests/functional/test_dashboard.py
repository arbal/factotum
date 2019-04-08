import csv
import time
from lxml import html

from django.urls import resolve
from django.test import TestCase

from dashboard.tests.loader import load_model_objects, fixtures_standard
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
        self.assertNotIn('QA', response_html.xpath('string(/html/body/nav//a[@href="/qa/extractionscript/"])'),
                         'The link to /qa/ should not appear in the public navbar')

    def test_logged_in_navbar(self):
        self.client.login(username='Karyn', password='specialP@55word')
        response = self.client.get('/').content.decode('utf8')
        response_html = html.fromstring(response)
        self.assertIn('QA', response_html.xpath('string(//*[@id="navbarQADropdownMenuLink"])'),
                      'The link to /qa/ must be in the logged-in navbar')
        found = resolve('/qa/extractionscript/')
        self.assertEqual(found.func, views.qa_extractionscript_index)

    def test_percent_extracted_text_doc(self):
        response = self.client.get('/').content.decode('utf8')
        response_html = html.fromstring(response)
        extracted_doc_count = response_html.xpath(
            '/html/body/div[1]/div[1]/div[4]/div/div')[0].text
        self.assertEqual('0%', extracted_doc_count)

        self.objects.doc.extracted = True
        self.objects.doc.save()
        response = self.client.get('/').content.decode('utf8')
        response_html = html.fromstring(response)
        extracted_doc_count = response_html.xpath(
            '/html/body/div[1]/div[1]/div[4]/div/div')[0].text
        self.assertEqual('100%', extracted_doc_count)

    def test_PUC_download(self):
        p = self.objects.puc
        puc_line = (p.gen_cat + ',' + p.prod_fam + ',' + p.prod_type + ',' + p.description +
                    ',' + str(p.get_level()) + ',' + str(p.product_count))
        # get csv
        response = self.client.get('/dl_pucs/')
        self.assertEqual(response.status_code, 200)
        csv_lines = response.content.decode('ascii').split('\r\n')
        # check header
        self.assertEqual(csv_lines[0], ('gen_cat,prod_fam,prod_type,description,'
                                        'PUC_type,num_prods'))
        # check the PUC from loader
        self.assertEqual(csv_lines[1], puc_line)


class DashboardTestWithFixtures(TestCase):
    fixtures = fixtures_standard

    def test_chemical_card(self):
        response = self.client.get('/').content.decode('utf8')
        self.assertIn('DSS Tox Chemicals', response,
                      'Where is the DSS Tox Chemicals card???')
        response_html = html.fromstring(response)
        num_dss = int(response_html.xpath('//*[@name="dsstox"]')[0].text)
        dss_table_count = DSSToxLookup.objects.count()
        self.assertEqual(num_dss, dss_table_count,
                         'The number shown should match the number of records in DSSToxLookup')


class DashboardTestWithFixtures(TestCase):
    fixtures = fixtures_standard

    def test_producttopuc_counts(self):
        response = self.client.get('/').content.decode('utf8')
        self.assertIn('Products Linked To PUC', response,
                      'Where is the Products Linked to PUC card???')
        response_html = html.fromstring(response)
        num_prods = int(response_html.xpath(
            '//*[@name="product_with_puc_count"]')[0].text)

        orm_prod_puc_count = ProductToPUC.objects.values(
            'product_id').distinct().count()
        self.assertEqual(num_prods, orm_prod_puc_count,
                         'The page should show %s Products linked to PUCs' % orm_prod_puc_count)

        # Assign an already-assigned product to a different PUC with a different method
        # and confirm that the count has not changed
        p2puc = ProductToPUC.objects.first()
        p2puc.id = None
        p2puc.classification_method = 'MB'
        p2puc.puc_id = 21
        p2puc.save()

        response = self.client.get('/').content.decode('utf8')
        response_html = html.fromstring(response)
        num_prods = int(response_html.xpath(
            '//*[@name="product_with_puc_count"]')[0].text)
        self.assertEqual(num_prods, orm_prod_puc_count,
                         'The page should show %s Products linked to PUCs' % orm_prod_puc_count)

        # Assign a previously unassigned product to a different PUC with a different method
        # and confirm that the count has gone up
        assigned_prods = ProductToPUC.objects.values_list('product_id')
        # print(assigned_prods)
        prod = Product.objects.exclude(id__in=assigned_prods).first()
        puc21 = PUC.objects.get(id=21)
        p2puc = ProductToPUC.objects.create(
            product=prod, puc=puc21, classification_method='MA')
        p2puc.save()

        response = self.client.get('/').content.decode('utf8')
        response_html = html.fromstring(response)
        num_prods = int(response_html.xpath(
            '//*[@name="product_with_puc_count"]')[0].text)
        self.assertEqual(num_prods, orm_prod_puc_count + 1,
                         'The page should show %s Products linked to PUCs' % str(orm_prod_puc_count + 1))
