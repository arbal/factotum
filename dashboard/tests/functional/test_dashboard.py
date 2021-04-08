import json

from django.test import TestCase, tag
from django.urls import resolve, reverse
from lxml import html

from dashboard import views
from dashboard.models import (
    PUCTag,
    PUCToTag,
    RawChem,
    ProductToPUC,
    Product,
    PUC,
    GroupType,
    DataDocument,
    DSSToxLookup,
)
from dashboard.tests.loader import load_model_objects, fixtures_standard


@tag("loader")
class DashboardTest(TestCase):
    def setUp(self):
        self.objects = load_model_objects()

    def test_public_navbar(self):
        self.client.logout()
        response = self.client.get("/").content.decode("utf8")
        response_html = html.fromstring(response)
        self.assertIn(
            "factotum",
            response_html.xpath('string(/html/body/nav//a[@href="/"]/text())'),
            "The app name factotum should appear in the public navbar",
        )
        self.assertIn(
            "Get Data",
            response_html.xpath('string(/html/body/nav//a[@href="/get_data/"]/text())'),
            "Get Data should appear in the public navbar",
        )
        self.assertIn(
            "Statistics",
            response_html.xpath(
                'string(/html/body/nav//a[@href="/statistics/"]/text())'
            ),
            "Statistics should appear in the public navbar",
        )
        self.assertIn(
            "Visualizations",
            response_html.xpath(
                'string(/html/body/nav//a[@href="/visualizations/"]/text())'
            ),
            "Visualizations should appear in the public navbar",
        )
        self.assertNotIn(
            "QA",
            response_html.xpath(
                'string(/html/body/nav//a[@href="/qa/extractionscript/"])'
            ),
            "The link to /qa/ should not appear in the public navbar",
        )

    def test_logged_in_navbar(self):
        self.client.login(username="Karyn", password="specialP@55word")
        response = self.client.get("/").content.decode("utf8")
        response_html = html.fromstring(response)
        self.assertIn(
            "QA",
            response_html.xpath('string(//*[@id="navbarQADropdownMenuLink"])'),
            "The link to /qa/ must be in the logged-in navbar",
        )
        found = resolve("/qa/extractionscript/")
        self.assertEqual(found.func, views.qa_extractionscript_index)

    @tag("puc")
    def test_PUC_download(self):
        puc = self.objects.puc

        allowedTag = PUCTag.objects.create(name="aerosol")
        PUCToTag.objects.create(tag=allowedTag, content_object=puc, assumed=False)

        assumedTag = PUCTag.objects.create(name="foamspray")
        PUCToTag.objects.create(tag=assumedTag, content_object=puc, assumed=True)

        # get csv
        response = self.client.get("/dl_pucs/")
        self.assertEqual(response.status_code, 200)
        csv_lines = response.content.decode("ascii").split("\r\n")
        # check header
        self.assertEqual(
            csv_lines[0],
            (
                "General category,Product family,Product type,"
                "Allowed attributes,Assumed attributes,Description,PUC type,PUC level,Product count,Cumulative product count"
            ),
        )
        # check the PUC from loader
        row1 = csv_lines[1].split(",")
        self.assertEqual(len(row1), 10)
        self.assertEqual(row1[0], "Test General Category")
        self.assertEqual(row1[1], "Test Product Family")
        self.assertEqual(row1[2], "Test Product Type")
        self.assertEqual(row1[3], "aerosol; foamspray")
        self.assertEqual(row1[4], "foamspray")
        self.assertEqual(row1[5], "Test Product Description")
        self.assertEqual(row1[6], "FO")
        self.assertEqual(row1[7], "3")
        self.assertEqual(row1[8], "0")

    def test_collapsible_tree_PUCs(self):
        # Keys that must be present at every level
        required_keys = ["name"]

        response = self.client.get(reverse("collapsible_tree_PUCs"))
        json_response_content = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json_response_content["name"], "Formulations")
        self._check_json_structure(json_response_content, required_keys)

    def _check_json_structure(self, json, required_keys):
        # This function recursively tests for keys at every level of a simple tree json response.
        for key in required_keys:
            self.assertTrue(key in json)

        if "children" in json:
            for i in range(len(json["children"])):
                self._check_json_structure(json["children"][i], required_keys)

    def test_grouptype_stats_table(self):
        grouptypescount = GroupType.objects.all().count()
        dsstox = DSSToxLookup.objects.create()

        response = self.client.get(reverse("grouptype_stats"))
        json_response_content = json.loads(response.content)

        # Add a document and a rawchem to verify count increments.
        DataDocument.objects.create(data_group=self.objects.dg)
        RawChem.objects.create(extracted_text=self.objects.extext, dsstox=dsstox)
        response_after_create = self.client.get(reverse("grouptype_stats"))
        json_response_content_after_create = json.loads(response_after_create.content)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            len(json_response_content["data"]),
            grouptypescount,
            "All Group Types should be represented.",
        )
        self.assertEqual(
            json_response_content["data"][0][0],
            "Composition",
            "Values should be ordered by the number of related documents",
        )
        self.assertEqual(
            json_response_content["data"][0][1],
            "1 (100%)",
            "documentcount returned seems to be incorrect information",
        )
        self.assertEqual(
            json_response_content["data"][0][2],
            "1 (100%)",
            "rawchemcount returned seems to be incorrect information",
        )
        self.assertEqual(
            json_response_content["data"][0][3],
            "0 (0%)",
            "curatedchemcount returned seems to be incorrect information",
        )
        self.assertEqual(
            json_response_content_after_create["data"][0][1],
            "2 (100%)",
            "Adding a data document should increase documentcount",
        )
        self.assertEqual(
            json_response_content_after_create["data"][0][2],
            "2 (100%)",
            "Adding a RawChem should increase rawchemcount",
        )
        self.assertEqual(
            json_response_content_after_create["data"][0][3],
            "1 (100%)",
            "Adding a Curated Chem should increase curatedchemcount",
        )

    def test_PUCTag_download(self):
        """check the PUCTag that would be downloaded from the loader"""
        pt = self.objects.pt
        response = self.client.get("/dl_puctags/")
        self.assertEqual(response.status_code, 200)
        csv_lines = response.content.decode("ascii").split("\r\n")
        self.assertEqual(csv_lines[0], ("Name,Definition"), "Check yo header.")
        row1 = csv_lines[1].split(",")
        self.assertEqual(row1[0], pt.name)
        self.assertEqual(row1[1], pt.definition)


class DashboardTestWithFixtures(TestCase):
    fixtures = fixtures_standard

    def test_chemical_card(self):
        response = self.client.get("/").content.decode("utf8")
        self.assertIn(
            "Unique DTXSID", response, "Where is the DSS Tox Chemicals card???"
        )
        response_html = html.fromstring(response)
        num_dss = int(response_html.xpath('//*[@name="dsstox"]')[0].text)
        dss_table_count = RawChem.objects.values("dsstox__sid").distinct().count()
        self.assertEqual(
            num_dss,
            dss_table_count,
            "The number shown should match the number DSSToxLookup SIDs with a matching RawChem record",
        )

    @tag("puc")
    def test_producttopuc_counts(self):
        response = self.client.get("/").content.decode("utf8")
        self.assertIn(
            "Products Linked To PUC",
            response,
            "Where is the Products Linked to PUC card???",
        )
        response_html = html.fromstring(response)

        chem_count = int(
            response_html.xpath(
                '//div[@class="card-body" and contains(h3, "Extracted Chemicals")]/div'
            )[0].text
        )
        self.assertEqual(RawChem.objects.count(), chem_count)

        num_prods = int(
            response_html.xpath('//*[@name="product_with_puc_count"]')[0].text
        )

        orm_prod_puc_count = (
            ProductToPUC.objects.values("product_id").distinct().count()
        )
        self.assertEqual(
            num_prods,
            orm_prod_puc_count,
            "The page should show %s Products linked to PUCs" % orm_prod_puc_count,
        )

        # Assign an already-assigned product to a different PUC with a different method
        # and confirm that the count has not changed
        p2puc = ProductToPUC.objects.first()
        p2puc.id = None
        p2puc.classification_method_id = "MB"
        p2puc.puc_id = 21
        p2puc.save()

        response = self.client.get("/").content.decode("utf8")
        response_html = html.fromstring(response)
        num_prods = int(
            response_html.xpath('//*[@name="product_with_puc_count"]')[0].text
        )
        self.assertEqual(
            num_prods,
            orm_prod_puc_count,
            "The page should show %s Products linked to PUCs" % orm_prod_puc_count,
        )

        # Assign a previously unassigned product to a different PUC with a different method
        # and confirm that the count has gone up
        assigned_prods = ProductToPUC.objects.values_list("product_id")
        prod = Product.objects.exclude(id__in=assigned_prods).first()
        puc21 = PUC.objects.get(id=21)
        p2puc = ProductToPUC.objects.create(
            product=prod, puc=puc21, classification_method_id="MA"
        )
        p2puc.save()

        response = self.client.get("/").content.decode("utf8")
        response_html = html.fromstring(response)
        num_prods = int(
            response_html.xpath('//*[@name="product_with_puc_count"]')[0].text
        )
        self.assertEqual(
            num_prods,
            orm_prod_puc_count + 1,
            "The page should show %s Products linked to PUCs"
            % str(orm_prod_puc_count + 1),
        )
