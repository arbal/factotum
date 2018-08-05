from django.urls import resolve
from django.test import TestCase
from django.http import HttpRequest
from dashboard.tests.loader import load_model_objects
from dashboard import views



class NavBarTest(TestCase):
    '''this group of tests checks to see that the URL resolves to the
    appropriate view function.
    '''
    def setUp(self):
        self.objects = load_model_objects()

    def test_home_page_returns_correct_html(self):
        # we need Karyn in the DB in order to log her in.
        # load_model_objects returns a `dot_notation` dict which we can
        # use all of the model objects from, seen in the print stmnt below.
        self.client.login(username='Karyn', password='specialP@55word')
        response = self.client.get('/')
        html = response.content.decode('utf8').rstrip()
        self.assertTrue(html.startswith('<!DOCTYPE html>'))
        self.assertIn('<title>factotum</title>', html)
        self.assertTrue(html.endswith('</html>'))

    def test_index_link(self):
        found = resolve('/')
        self.assertEqual(found.func, views.index)

    def test_data_sources_link(self):
        found = resolve('/datasources/')
        self.assertEqual(found.func, views.data_source_list)

    def test_product_curation_link(self):
        found = resolve('/product_curation/')
        self.assertEqual(found.func, views.product_curation_index)

    def test_qa_link(self):
        found = resolve('/qa/')
        self.assertEqual(found.func, views.qa_index)
