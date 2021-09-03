import base64
import re

from lxml import html

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from dashboard.tests.loader import *
from django.contrib.sessions.middleware import SessionMiddleware
import requests
from django.test import TestCase, RequestFactory
from django.conf import settings

import bs4
import json

from elastic.models import QueryLog
from dashboard.views.search import search_model
from dashboard.tests.elastic_factories import fetch_dashboard_logstash
from dashboard.tests.factories import DataDocumentFactory, ProductFactory
from django.contrib.auth.models import User


class TestSearch(TestCase):
    multi_db = True
    fixtures = fixtures_standard

    def setUp(self):
        self.factory = RequestFactory()
        self.client.login(username="Karyn", password="specialP@55word")
        self.esurl = settings.ELASTICSEARCH["default"]["HOSTS"][0]
        self.index = settings.ELASTICSEARCH["default"]["INDEX"]
        (self.es_username, self.es_password) = settings.ELASTICSEARCH["default"][
            "HTTP_AUTH"
        ]
        self.auth_header = {
            "Authorization": "Basic "
            + base64.b64encode(
                f"{self.es_username}:{self.es_password}".encode("utf-8")
            ).decode("utf-8")
        }

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
        response = requests.get(f"http://{self.esurl}", headers=self.auth_header)
        self.assertTrue(response.status_code == 200)

        response = requests.get(
            f"http://{self.esurl}/{self.index}/_search?q=ethylparaben",
            headers=self.auth_header,
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
        string = "Number of products related to document: 1"
        self.assertIn(string, str(response.content))

        response = self.client.get("/search/puc/?q=" + b64)
        string = "Arts and crafts/Office supplies"
        self.assertIn(string, str(response.content))

        response = self.client.get("/search/chemical/?q=" + b64)
        string = "DTXSID6026296"
        self.assertIn(string, str(response.content))

    def test_pagination(self):
        """
        The results are paginated by the correct amount
        """
        qs = self._get_query_str("water")
        response = self.client.get("/search/datadocument/" + qs)
        response_html = html.fromstring(response.content.decode("utf8"))
        element_count = len(
            response_html.xpath(
                '//*[contains(concat(" ", normalize-space(@class), " ")," resultrow ")]'
            )
        )
        self.assertEqual(element_count, 40)

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
        expected_total = "43 datadocuments"  # includes "eau" and "H2O" synonyms
        self.assertIn(expected_total, total_took)
        # pucs
        response = self.client.get("/search/puc/" + qs)
        response_html = html.fromstring(response.content.decode("utf8"))
        total_took = response_html.xpath('normalize-space(//*[@id="total-took"])')
        expected_total = "13 pucs"  # includes synonyms
        self.assertIn(expected_total, total_took)
        # chemicals
        response = self.client.get("/search/chemical/" + qs)
        response_html = html.fromstring(response.content.decode("utf8"))
        total_took = response_html.xpath('normalize-space(//*[@id="total-took"])')
        expected_total = "1 chemicals"
        self.assertIn(expected_total, total_took)

    def test_model_counts(self):
        qs = self._get_query_str("water")
        response = self.client.get("/search/product/" + qs)
        counts = response.wsgi_request.session["unique_counts"]
        self.assertIsNotNone(counts)
        self.assertEquals(counts["datadocument"], 43)
        self.assertEquals(counts["product"], 7)
        self.assertEquals(counts["chemical"], 1)
        self.assertEquals(counts["puc"], 13)

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

    def test_anonymous_read(self):
        self.client.logout()
        response = self.client.get("/")
        response_html = response.content.decode("utf8")
        self.assertIn('placeholder="Search"', response_html)

        qs = self._get_query_str("ethylparaben")
        response = self.client.get("/search/datadocument/" + qs)
        response_html = response.content.decode("utf8")
        self.assertIn("<em>Benzoic acid</em>", response_html)

    def test_logging(self):
        query = "a wild and wonderful query"
        # Test selective logging
        qs = self._get_query_str(query)
        pre_count = QueryLog.objects.all().count()
        self.client.get("/search/product/" + qs)
        self.client.get("/search/datadocument/" + qs)
        self.client.get("/search/product/" + qs + "&page=2")
        self.client.get("/search/product/" + qs + "&product_brandname=test")
        self.client.get("/search/tag/" + qs)
        post_count = QueryLog.objects.all().count()
        self.assertTrue(
            post_count - pre_count <= 1, "Only the initial query should be logged."
        )

        # Test log entry
        User = get_user_model()
        user = User.objects.get(username="Karyn")
        application = QueryLog.FACTOTUM
        querylog = QueryLog.objects.filter(query=query).first()
        self.assertEqual(querylog.query, query, "The query was not correctly logged.")
        self.assertEqual(
            querylog.user_id, user.pk, "The user was not correctly logged."
        )
        self.assertEqual(
            querylog.application,
            application,
            "The application was not correctly logged.",
        )

        # Test character limit
        max_q_size = 255
        long_query = query * (max_q_size // len(query) + 1)
        long_qs = self._get_query_str(long_query)
        pre_count = QueryLog.objects.all().count()
        response = self.client.get("/search/product/" + long_qs)
        post_count = QueryLog.objects.all().count()
        self.assertTrue(
            post_count - pre_count == 0, "A query over 255 should not be logged."
        )
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertIn(
            "Please limit your query to 255 characters.",
            messages,
            "Error should be thrown for query longer than 255 characters.",
        )

    def test_chemical_captions(self):
        """
        Searching by chemical name should return the CAS without any highlights,
        searching by CAS should return a highlighted element
        """
        qs = self._get_query_str("water")
        resp = self.client.get("/search/chemical/" + qs)
        soup = bs4.BeautifulSoup(resp.content, features="lxml")
        selector = soup.find_all(text="7732-18-5")[0]
        self.assertEqual(selector, "7732-18-5")

        qs = self._get_query_str("7732-18-5")
        resp = self.client.get("/search/chemical/" + qs)
        soup = bs4.BeautifulSoup(resp.content, features="lxml")
        selector = soup.find_all(text="7732-18-5")[0]
        self.assertEqual(str(selector.parent), "<em>7732-18-5</em>")

    def test_document_search_product_count(self):
        """
        Searching for documents should return a list of data documents and
        their associated product count
        """
        qs = self._get_query_str("water")
        resp = self.client.get("/search/datadocument/" + qs)
        soup = bs4.BeautifulSoup(resp.content, features="lxml")
        # Filter down results to the 2 that are being tested
        test_divs = []
        for result in soup.find_all("div", class_="resultrow"):
            valid_div = result.find(
                text=[
                    re.compile("Nonflammable Gas Mixture: Nitrogen / Oxygen / "),
                    re.compile(
                        "TRENDstarter Hard Gel 5.1 fl oz / \(New York Value Club\)"
                    ),
                ]
            )
            if valid_div:
                test_divs.append(result)
        # Verify correct number of results returned.
        self.assertEqual(len(test_divs), 2, "Search did not provide correct results")
        # Test first result for correct document count
        self.assertIn(
            "Nonflammable Gas Mixture:",
            test_divs[0].get_text(),
            'First result for water is not "Nonflammable Gas Mixture"',
        )
        self.assertIn(
            "Number of products related to document: 0",
            test_divs[0].get_text(),
            "Nonflammable Gas Mixture has the incorrect number of associated products",
        )
        # Test second result for correct document count
        self.assertIn(
            "TRENDstarter Hard Gel 5.1 fl oz",
            test_divs[1].get_text(),
            'Second result for water is not "TRENDstarter Hard Gel 5.1 fl oz"',
        )
        self.assertIn(
            "Number of products related to document: 1",
            test_divs[1].get_text(),
            "TRENDstarter Hard Gel 5.1 fl oz has the incorrect number of associated products",
        )

    def test_puc_search_product_count(self):
        """
        Searching for PUCs should return a list of PUCs and
        their associated product count
        """
        qs = self._get_query_str("water")
        resp = self.client.get("/search/puc/" + qs)
        soup = bs4.BeautifulSoup(resp.content, features="lxml")
        # Filter down results to the 2 that are being tested
        test_divs = []
        for result in soup.find_all("a", href=["/puc/245/", "/puc/137/"]):
            test_divs.append(result.parent.parent)

        # Verify correct number of results returned.
        self.assertEqual(len(test_divs), 2, "Search did not provide correct results")
        # Test first result for correct document count
        self.assertIn(
            "bubble bath",
            test_divs[0].get_text(),
            'First result for water is not "bubble bath"',
        )
        self.assertIn(
            "Number of products related to PUC: 1",
            test_divs[0].get_text(),
            "Bubble bath has the incorrect number of associated products",
        )
        # Test second result for correct document count
        self.assertIn(
            "Personal care --",
            test_divs[1].get_text(),
            'Second result for water is not "Personal Care --"',
        )
        self.assertIn(
            "Number of products related to PUC: 2",
            test_divs[1].get_text(),
            "Personal Care has the incorrect number of associated products",
        )

    def test_boosted_fields(self):
        """
        A search for "water" should score a document with "water" (or
        a synonym) in its chemicals' true chem names higher
        than a document with "water" in its title.
        """
        # The first result row should contain "True chemical name:"
        qs = self._get_query_str("water")
        resp = self.client.get("/search/datadocument/" + qs)
        soup = bs4.BeautifulSoup(resp.content, features="lxml")
        divs = soup.find_all("div", {"class": "resultrow"})
        self.assertInHTML("True chemical name:", str(divs[0]))

        # The example document 156624 with "water" only in its title
        # should be all the way on the fifth page
        resp = self.client.get("/search/datadocument/" + qs + "&page=2")
        self.assertIn("/datadocument/156624/", str(resp.content))

    def test_chemical_fields(self):
        """
        Chemical search results should only return "Preferred name" and "Preferred CAS"
        Additional fields that may be used as search criteria should not show up.
        """
        qs = self._get_query_str("none")
        resp = self.client.get("/search/chemical/" + qs)
        soup = bs4.BeautifulSoup(resp.content, features="lxml")
        divs = soup.find_all("div", {"class": "resultrow"})
        self.assertInHTML("Preferred chemical name:", str(divs[0]))
        self.assertInHTML("Preferred CAS:", str(divs[0]))

    def test_search_tag(self):
        name = "absorbent"
        qs = self._get_query_str(name)
        response = self.client.get("/search/tag/" + qs)
        response_html = html.fromstring(response.content.decode("utf8"))

        self.assertIn(name, str(response.content))
        tag_link = "/list_presence_tag/2/"
        self.assertIn(tag_link, str(response.content))
        expected_total = "1 tags returned in"
        total_took = response_html.xpath('normalize-space(//*[@id="total-took"])')
        self.assertIn(expected_total, total_took)

    def test_phrase_search(self):
        """
        Using a quoted string should promote the phrase in the results
        """

        # Use factories, since there need to be more products and documents than
        # the fixtures include
        doc_count = 12
        datadocs = []
        for i in range(doc_count):
            new_title = "Shampoo " + str(i)
            if i % 4 == 0:
                new_title = (
                    "Pet "
                    + new_title  # every fourth document should be called "Pet Shampoo _"
                )
            # using the "test_phrase_search" subtitle will allow the tearDown() method to find
            # these documents and delete them
            doc = DataDocumentFactory(
                title=new_title,
                subtitle="test_phrase_search",
                product=[ProductFactory(title=new_title)],
            )
            datadocs.append(doc)

        # create the WHERE clause out of the new docs
        where_batch = "WHERE dd.id IN ("
        for doc in datadocs:
            where_batch = where_batch + str(doc.id) + ", "
        where_batch = where_batch + " -99)"  # close out the WHERE clause

        # once the documents and products have been added, get the JSON
        # for POSTing them to the search index
        docs_json = fetch_dashboard_logstash(where=where_batch)

        for doc_dict in docs_json:
            # add the JSON to the index
            response = requests.post(
                f"http://{self.esurl}/dashboard/_doc/",
                json=doc_dict,
                headers=self.auth_header,
            )
            self.assertEqual(201, response.status_code)
        
        # refresh the index before proceeding
        requests.post(
            f"http://{self.esurl}/dashboard/_refresh/",
            headers=self.auth_header,
        )

        # Unquoted search should return records with just "shampoo"

        b64 = base64.b64encode(b"pet shampoo").decode("unicode_escape")
        response = self.client.get("/search/product/?q=" + b64)
        soup = bs4.BeautifulSoup(response.content, features="lxml")
        hits = soup.find_all("h5", {"class": "hit-header"})
        self.assertEqual(
            len(hits), 13, "There should be 13 results for the unquoted search"
        )

        # Quoted search should only return records with "pet shampoo"

        b64 = base64.b64encode(b'"pet shampoo"').decode("unicode_escape")
        response = self.client.get("/search/product/?q=" + b64)
        soup = bs4.BeautifulSoup(response.content, features="lxml")
        hits = soup.find_all("h5", {"class": "hit-header"})
        self.assertEqual(
            len(hits), 3, "There should be 3 results for the quoted search"
        )
        # the result counts in the tabs should match the other counts
        nav_tabs = soup.find('ul', attrs={'class': 'nav-tabs'})
        badges = nav_tabs.find_all("span", {"class": "badge-light"})
        # Products,  Documents, PUCs, Chemicals, Tags 
        self.assertEqual(
            str(len(hits)), badges[0].text, "The result count in the Products badge should match the number of h5 elements below"
        )

        # single quotes should have the same behavior
        b64 = base64.b64encode(b"'pet shampoo'").decode("unicode_escape")
        response = self.client.get("/search/product/?q=" + b64)
        soup = bs4.BeautifulSoup(response.content, features="lxml")
        hits = soup.find_all("h5", {"class": "hit-header"})
        self.assertEqual(
            len(hits), 3, "There should be 3 results for the quoted search"
        )
        # the result counts in the tabs should match the other counts
        nav_tabs = soup.find('ul', attrs={'class': 'nav-tabs'})
        badges = nav_tabs.find_all("span", {"class": "badge-light"})
        # Products,  Documents, PUCs, Chemicals, Tags 
        self.assertEqual(
            str(len(hits)), badges[0].text, "The result count in the Products badge should match the number of h5 elements below"
        )

        # Delete the documents that were added to the index for the purposes of the test
        delete_json = {
            "query": {"match": {"datadocument_subtitle": "test_phrase_search"}}
        }

        cleanup_response = requests.post(
            f"http://{self.esurl}/dashboard/_delete_by_query/",
            json=delete_json,
            headers=self.auth_header,
        )
        self.assertEqual(200, cleanup_response.status_code)
        requests.post(
            f"http://{self.esurl}/dashboard/_refresh/",
            headers=self.auth_header,
        )


class TestSearchView(TestCase):
    fixtures = fixtures_standard

    def setUp(self):
        # Every test needs access to the request factory.
        self.request_factory = RequestFactory()
        self.user = User.objects.get(username="Karyn")
        self.esurl = settings.ELASTICSEARCH["default"]["HOSTS"][0]
        self.index = settings.ELASTICSEARCH["default"]["INDEX"]
        (self.es_username, self.es_password) = settings.ELASTICSEARCH["default"][
            "HTTP_AUTH"
        ]
        self.auth_header = {
            "Authorization": "Basic "
            + base64.b64encode(
                f"{self.es_username}:{self.es_password}".encode("utf-8")
            ).decode("utf-8")
        }

    def tearDown(self):
        # Delete the documents that were added to the index for the purposes of the test
        delete_json = {
            "query": {"match": {"datadocument_subtitle": "test_special_search"}}
        }

        cleanup_response = requests.post(
            f"http://{self.esurl}/dashboard/_delete_by_query/",
            json=delete_json,
            headers=self.auth_header,
        )
        self.assertEqual(200, cleanup_response.status_code)
        requests.post(
            f"http://{self.esurl}/dashboard/_refresh/",
            headers=self.auth_header,
        )

    def test_special_char_search(self):
        """
        Users should be able to use search strings that contain special
        characters, like:
        'normal/ oily' 
        '(-)-beta-Pinene'
        'bath $10'
        """
        datadocs = []
        search_terms = ["normal/ oily", "(-)-beta-Pinene", "bath $10"]
        for term in search_terms:
            doc = DataDocumentFactory(
                title=term,
                subtitle="test_special_search",
                product=[ProductFactory(title=term)],
            )
            datadocs.append(doc)

        # create the WHERE clause out of the new docs
        where_batch = "WHERE dd.id IN ("
        for doc in datadocs:
            where_batch = where_batch + str(doc.id) + ", "
        where_batch = where_batch + " -99)"  # close out the WHERE clause

        # once the documents and products have been added, get the JSON
        # for POSTing them to the search index
        docs_json = fetch_dashboard_logstash(where=where_batch)

        for doc_dict in docs_json:
            # add the JSON to the index
            response = requests.post(
                f"http://{self.esurl}/dashboard/_doc/",
                json=doc_dict,
                headers=self.auth_header,
            )
            self.assertEqual(201, response.status_code)
            requests.post(
                f"http://{self.esurl}/dashboard/_refresh/",
                headers=self.auth_header,
            )

        # test the search terms
        for term in search_terms:
            # put quotes around the search term to minimize other results
            term = f'"{term}"'
            q = base64.b64encode(term.encode()).decode("unicode_escape")
            request = self.request_factory.get("/search/product", {"q": q})

            middleware = SessionMiddleware()
            middleware.process_request(request)
            request.session.save()
            request.user = self.user

            response = search_model(request, "product")

            self.assertEqual(response.status_code, 200)
            soup = bs4.BeautifulSoup(response.content, features="lxml")
            hits = soup.find_all("h5", {"class": "hit-header"})
            self.assertEqual(
                len(hits), 1, f"Searching for {term} should return 1 result "
            )
