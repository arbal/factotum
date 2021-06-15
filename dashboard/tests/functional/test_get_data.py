from django.contrib.auth.models import User
from django.test import TestCase, override_settings, tag
from django.test.client import Client
from django.urls import reverse

from dashboard.models import (
    DSSToxLookup,
    DataDocument,
    ExtractedComposition,
    Product,
    ProductDocument,
    ProductToPUC,
    PUC,
    FunctionalUseCategory,
)
from dashboard.tests.loader import fixtures_standard
from dashboard.views.get_data import stats_by_dtxsids


@override_settings(ALLOWED_HOSTS=["testserver"])
class TestGetData(TestCase):
    fixtures = fixtures_standard

    def setUp(self):
        self.client = Client()

    def test_dtxsid_pucs_n(self):
        dtxs = ["DTXSID9022528", "DTXSID1020273", "DTXSID6026296", "DTXSID2021781"]
        # Functional test: the stats calculation
        stats = stats_by_dtxsids(dtxs)
        # select out the stats for one DTXSID, ethylparaben
        ethylparaben_stats = stats.get(sid="DTXSID9022528")
        dsstox = DSSToxLookup.objects.get(sid="DTXSID9022528")
        self.assertEqual(
            dsstox.get_puc_count(),
            ethylparaben_stats["pucs_n"],
            (
                f"There should be {dsstox.get_puc_count()}) "
                "PUC associated with ethylparaben"
            ),
        )

        self.client.login(username="Karyn", password="specialP@55word")
        # get the associated documents for linking to products
        dds = DataDocument.objects.filter(
            pk__in=ExtractedComposition.objects.filter(
                dsstox__sid="DTXSID9022528"
            ).values("extracted_text__data_document")
        )
        dd = dds[0]
        p = Product.objects.create(
            title="Test Product", upc="Test UPC for ProductToPUC"
        )
        ProductDocument.objects.create(document=dd, product=p)
        dd.refresh_from_db()

        # get one of the products that was just linked to a data document with DTXSID9022528 in its extracted chemicals
        pid = dd.products.first().pk
        puc = PUC.objects.get(id=20)
        # add a puc to one of the products containing ethylparaben

        ppuc = ProductToPUC.objects.create(
            product=Product.objects.get(pk=pid),
            puc=puc,
            puc_assigned_usr=User.objects.get(username="Karyn"),
            classification_method_id="MA",
        )
        ppuc.refresh_from_db()
        stats = stats_by_dtxsids(dtxs)
        # select out the stats for one DTXSID, ethylparaben
        ethylparaben_stats = stats.get(sid="DTXSID9022528")
        self.assertEqual(dsstox.get_puc_count(), ethylparaben_stats["pucs_n"])

    def test_dtxsid_dds_n(self):
        dtxs = ["DTXSID9022528", "DTXSID1020273", "DTXSID6026296", "DTXSID2021781"]
        # Functional test: the stats calculation
        stats = stats_by_dtxsids(dtxs)
        for e in stats:
            if e["sid"] == "DTXSID9022528":
                ethylparaben_stats = e

        self.assertEqual(
            3,
            ethylparaben_stats["dds_n"],
            "There should be 2 datadocuments associated with ethylaraben",
        )
        # change the number of related data documents by deleting one
        self.client.login(username="Karyn", password="specialP@55word")
        # get the associated documents for linking to products
        dds = DataDocument.objects.filter(
            pk__in=ExtractedComposition.objects.filter(
                dsstox__sid="DTXSID9022528"
            ).values("extracted_text__data_document")
        )

        dd = dds[0]
        dd.delete()

        stats = stats_by_dtxsids(dtxs)
        for e in stats:
            if e["sid"] == "DTXSID9022528":
                ethylparaben_stats = e

        self.assertEqual(
            1,
            ethylparaben_stats["dds_n"],
            "There should now be 1 datadocument associated with ethylaraben",
        )

    def test_dtxsid_dds_wf_n(self):
        dtxs = ["DTXSID9022528", "DTXSID1020273", "DTXSID6026296", "DTXSID2021781"]
        # Functional test: the stats calculation
        stats = stats_by_dtxsids(dtxs)
        for e in stats:
            if e["sid"] == "DTXSID9022528":
                ethylparaben_stats = e
        self.assertEqual(
            1,
            ethylparaben_stats["dds_wf_n"],
            "There should be 1 extracted chemical \
        with weight fraction data associated with ethylparaben",
        )
        # add weight fraction data to a different extractedcomposition
        ec = ExtractedComposition.objects.get(rawchem_ptr_id=73)
        ec.raw_min_comp = 0.1
        ec.save()
        stats = stats_by_dtxsids(dtxs)
        for e in stats:
            if e["sid"] == "DTXSID9022528":
                ethylparaben_stats = e

        self.assertEqual(
            2,
            ethylparaben_stats["dds_wf_n"],
            "There should be 2 extracted chemicals \
        with weight fraction data associated with ethylparaben",
        )

    def test_dtxsid_products_n(self):
        dtxs = ["DTXSID9022528", "DTXSID1020273", "DTXSID6026296", "DTXSID2021781"]
        # Functional test: the stats calculation
        stats = stats_by_dtxsids(dtxs)

        for e in stats:
            if e["sid"] == "DTXSID9022528":
                ethylparaben_stats = e

        self.assertEqual(
            6,
            ethylparaben_stats["products_n"],
            "There should be 6 products associated with ethylparaben",
        )
        self.client.login(username="Karyn", password="specialP@55word")
        # get the associated documents for linking to products
        dds = DataDocument.objects.filter(
            pk__in=ExtractedComposition.objects.filter(
                dsstox__sid="DTXSID9022528"
            ).values("extracted_text__data_document")
        )
        dd = dds[0]
        p = Product.objects.create(
            title="Test Product", upc="Test UPC for ProductToPUC"
        )
        ProductDocument.objects.create(document=dd, product=p)
        dd.refresh_from_db()

        stats = stats_by_dtxsids(dtxs)
        for e in stats:
            if e["sid"] == "DTXSID9022528":
                ethylparaben_stats = e
        self.assertEqual(
            8,
            ethylparaben_stats["products_n"],
            "There should now be 8 products associated with ethylparaben",
        )

    @tag("puc")
    def test_habits_and_practices_cards(self):
        data = {"puc": ["2"]}
        response = self.client.post("/get_data/", data=data)
        for hnp in [b"ball bearings", b"motorcycle", b"vitamin a&amp;d", b"dish soap"]:
            self.assertIn(hnp, response.content)

    def test_download_buttons_and_links(self):
        response = self.client.get("/get_data/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Download PUCs")
        self.assertContains(response, reverse("puc_list"))
        self.assertContains(response, "Download PUC Attributes")
        self.assertContains(response, "Download List Presence Keywords")
        self.assertContains(response, reverse("list_presence_tag_list"))
        self.assertContains(response, "Download Functional Use Categories")
        self.assertContains(response, reverse("functional_use_category_list"))

    def test_download_list_presence_keywords(self):
        response = self.client.get("/dl_lpkeywords/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "abrasive")
        self.assertContains(response, "Velit neque aliquam etincidunt.")
        self.assertContains(response, "General use")

    def test_download_functional_use_categories(self):
        response = self.client.get("/dl_functionalusecategories/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "fragrance")
        self.assertContains(response, "surfactant,surfactant")

    def test_function_user_categories_page(self):
        response = self.client.get(reverse("functional_use_category_list"))
        self.assertEqual(response.status_code, 200)
        categories = FunctionalUseCategory.objects.all()
        for cat in categories:
            self.assertContains(response, cat.title)
            self.assertContains(response, cat.description)

    def test_download_functional_uses(self):
        response = self.client.get("/dl_functional_uses/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Sun Ingredient Disclosures,Composition,Sun_INDS_89,2018-04-07,ethylparabenzene,120-47-9,DTXSID9022528,ethylparaben,120-47-8,False,kayaking,fragrance",
        )
