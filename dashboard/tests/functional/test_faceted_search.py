from django.test import TestCase
from django.test.client import Client
from lxml import html

from django.urls import resolve
from django.contrib.auth.models import User
from dashboard.tests.loader import fixtures_standard


class FacetedSearchTest(TestCase):
    fixtures = fixtures_standard

    def setUp(self):
        self.c = Client()

    def test_faceted_search_excludes_chemicals(self):
        response = self.c.get('/find/?q=ethyl')
        self.assertContains(response, 'Data Document')
        self.assertNotContains(response, 'Extracted Chemical')
        self.assertNotContains(response, 'DSSTox Substance')

    def test_faceted_search_returns_upc(self):
        response = self.c.get('/find/?q=avcat')
        self.assertContains(response, 'stub_1845')


    def test_group_type_facet(self):
        response = self.c.get('/find/?q=diatom')
        self.assertContains(response, 'Filter by Group Type')

        response = self.c.get('/find/?q=diatom&group_type=Unidentified')
        self.assertContains(response, 'Showing 1 - 20 of')

        response = self.c.get('/find/?q=diatom&group_type=BadGroupName')
        self.assertContains(response, 'Sorry, no result found')

    def test_faceted_search_renders_div(self):
        response = self.c.get('/find/?q=terro')
        self.assertNotContains(response, '<table')
        self.assertContains(response, '<div class="results-wrapper">')

    def test_product_facet_returns(self):
        response = self.c.get('/find/?q=insecticide')
        brands = response.content.count(b'name="brand_name"')
        # default set to options = {"size": 0} in /dashboard/views/search.py
        self.assertTrue(brands>10, ('There should be ~143 product returns '
                                                        'for this search term'))
