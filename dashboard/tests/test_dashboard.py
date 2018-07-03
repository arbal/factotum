import time
from django.urls import resolve
from django.test import TestCase
from .loader import load_model_objects
from dashboard import views
from lxml import html

class DashboardTest(TestCase):

    def setUp(self):
        self.objects = load_model_objects()
        self.test_start = time.time()

    def tearDown(self):
        self.test_elapsed = time.time() - self.test_start
        print('\nFinished with ' + self._testMethodName + ' in {:.2f}s'.format(self.test_elapsed))

    def test_public_navbar(self):
        self.client.logout()
        response = self.client.get('/').content.decode('utf8')
        response_html = html.fromstring(response)
        self.assertIn('factotum', response_html.xpath('string(/html/body/nav//a[@href="/login/"]/text())'),
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
