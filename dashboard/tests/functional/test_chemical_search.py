from django.test import Client
from dashboard.tests.loader import *
import requests
from django.test import TestCase, RequestFactory
from factotum import settings

class TestChemicalSearch(TestCase):
    fixtures = fixtures_standard

    def setUp(self):
        self.factory = RequestFactory()
        self.client.login(username='Karyn', password='specialP@55word')
        self.esurl = f'http://{settings.ELASTIC_HOST}:{settings.ELASTIC_PORT}'

    def test_search_api(self):
        """
        The correct JSON comes back from the elasticsearch server
        """
        response = requests.get(self.esurl)
        self.assertTrue(response.ok)
        
        response = requests.get(f'{self.esurl}/factotum_chemicals/_search?q=ethylparaben')
        self.assertIn('DTXSID9022528', str(response.content))

    def test_results_page(self):
        """
        The result page returns the correct content
        """
        response = self.client.get('/search/es_chemicals/?q=ethylparaben')
        
        prod_count_html = "2 products associated with this document"
        self.assertIn(prod_count_html, str(response.content))

        document_count_html = "2 documents returned in"
        self.assertIn(document_count_html, str(response.content))

        puc_count_html = "2 PUCs returned in"
        self.assertIn(puc_count_html, str(response.content))
