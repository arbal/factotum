import base64
from lxml import html

from django.test import Client
from dashboard.tests.loader import *
import requests
from django.test import TestCase, RequestFactory
from factotum import settings


class TestSearch(TestCase):
    fixtures = fixtures_standard

    def setUp(self):
        self.factory = RequestFactory()
        self.client.login(username="Karyn", password="specialP@55word")
        self.esurl = settings.ELASTICSEARCH["default"]["HOSTS"][0]
        self.index = settings.ELASTICSEARCH["default"]["INDEX"]

    def _b64_str(self, s):
        return base64.b64encode(s.encode()).decode("unicode_escape")

    def _get_query_str(self, q, facets={}):
        q_b64 = "?q=" + self._b64_str(q)
        facets_b64_arr = []
        for facet_name, facet_arr in facets.items():
            b64_str = ",".join(self._b64_str(s) for s in facet_arr)
            facets_b64_arr.append(facet_name + "=" + b64_str)
        if facets_b64_arr:
            facets_b64 = "&" + "&".join(facets_b64_arr)
        else:
            facets_b64 = ""
        return q_b64 + facets_b64

    def test_search_api(self):
        """
        The correct JSON comes back from the elasticsearch server
        """
        response = requests.get(f"http://{self.esurl}")
        self.assertTrue(response.ok)

        response = requests.get(
            f"http://{self.esurl}/{self.index}/_search?q=ethylparaben"
        )
        self.assertIn("DTXSID9022528", str(response.content))

    def test_results_page(self):
        """
        The result page returns the correct content
        """
        b64 = base64.b64encode(b"water").decode("unicode_escape")

        response = self.client.get("/search/product/?q=" + b64)
        string = "Mama Bee Soothing Leg"
        self.assertIn(string, str(response.content))

        response = self.client.get("/search/datadocument/?q=" + b64)
        string = "Number of products related to chemical: 1"
        self.assertIn(string, str(response.content))

        response = self.client.get("/search/puc/?q=" + b64)
        string = "Arts and crafts/Office supplies"
        self.assertIn(string, str(response.content))

        response = self.client.get("/search/chemical/?q=" + b64)
        string = "DTXSID6026296"
        self.assertIn(string, str(response.content))

    def test_number_returned(self):
        # products
        qs = self._get_query_str("water")
        response = self.client.get("/search/product/" + qs)
        response_html = html.fromstring(response.content.decode("utf8"))
        total_took = response_html.xpath('normalize-space(//*[@id="total-took"])')
        expected_total = "7 products"  # This includes "eau" synonym records
        self.assertIn(expected_total, total_took)
        # documents
        response = self.client.get("/search/datadocument/" + qs)
        response_html = html.fromstring(response.content.decode("utf8"))
        total_took = response_html.xpath('normalize-space(//*[@id="total-took"])')
        expected_total = "42 datadocuments"  # includes "eau" and "H2O" synonyms
        self.assertIn(expected_total, total_took)
        # pucs
        response = self.client.get("/search/puc/" + qs)
        response_html = html.fromstring(response.content.decode("utf8"))
        total_took = response_html.xpath('normalize-space(//*[@id="total-took"])')
        expected_total = "12 pucs"  # includes synonyms
        self.assertIn(expected_total, total_took)
        # chemicals
        response = self.client.get("/search/chemical/" + qs)
        response_html = html.fromstring(response.content.decode("utf8"))
        total_took = response_html.xpath('normalize-space(//*[@id="total-took"])')
        expected_total = "1 chemicals"
        self.assertIn(expected_total, total_took)

    def test_facets(self):
        qs = self._get_query_str("water", {"product_brandname": ["3M"]})
        response = self.client.get("/search/product/" + qs)
        response_html = html.fromstring(response.content.decode("utf8"))
        total_took = response_html.xpath('normalize-space(//*[@id="total-took"])')
        expected_total = "1 products returned"
        self.assertIn(expected_total, total_took)

    def test_input(self):
        # Test ampersand
        qs = self._get_query_str("Rubber & Vinyl 80 Spray Adhesive")
        response = self.client.get("/search/product/" + qs)
        response_html = html.fromstring(response.content.decode("utf8"))
        total_took = response_html.xpath('normalize-space(//*[@id="total-took"])')
        expected_total = "3 products returned"
        self.assertIn(expected_total, total_took)

        # Test comma
        qs = self._get_query_str("2,6-Di-tert-butyl-p-cresol")
        response = self.client.get("/search/product/" + qs)
        response_html = html.fromstring(response.content.decode("utf8"))
        total_took = response_html.xpath('normalize-space(//*[@id="total-took"])')
        expected_total = "1 products returned in"
        self.assertIn(expected_total, total_took)

    def test_synonyms(self):
        # Test benzoic acid => ethylparaben
        qs = self._get_query_str("ethylparaben")
        response = self.client.get("/search/datadocument/" + qs)
        response_html = response.content.decode("utf8")
        self.assertIn("<em>Benzoic acid</em>", response_html)
