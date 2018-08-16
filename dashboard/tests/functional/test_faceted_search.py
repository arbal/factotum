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
    
    def test_group_type_facet(self):
        response = self.c.get('/find/?q=diatom')
        self.assertContains(response, 'Filter by Group Type')
        
        response = self.c.get('/find/?q=diatom&group_type=Unidentified')
        self.assertContains(response, 'Showing 1 - 20 of')

        response = self.c.get('/find/?q=diatom&group_type=BadGroupName')
        self.assertContains(response, 'Sorry, no result found')



