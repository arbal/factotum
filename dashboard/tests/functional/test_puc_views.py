from lxml import html
import json

from django.test import TestCase, override_settings

from dashboard.models import PUC
from django.db.models import Count
from dashboard.tests.loader import fixtures_standard


@override_settings(ALLOWED_HOSTS=["testserver"])
class TestPUCViews(TestCase):
    fixtures = fixtures_standard

    def test_puc_not_specified(self):
        response = self.client.get("/puc/20/").content.decode("utf8")
        response_html = html.fromstring(response)
        asumeBtns = response_html.xpath('//*[@id="assumed_attributes"]/button')
        self.assertTrue(
            len(asumeBtns) == 2, "Two assumed tags should exist for this PUC."
        )
        for button in asumeBtns:
            self.assertTrue(button.get("title"), "Button should have tooltip.")
        allowBtns = response_html.xpath('//*[@id="allowed_attributes"]/button')
        self.assertTrue(
            len(allowBtns) == 7, "Seven allowed tags should exist for this PUC."
        )
        for button in allowBtns:
            self.assertTrue(button.get("title"), "Button should have tooltip.")

    def test_puc_type_specified(self):
        response = self.client.get("/puc/62/").content.decode("utf8")
        response_html = html.fromstring(response)
        prod_fam = response_html.xpath('//*[@id="puc_prod_fam"]/text()')
        self.assertIn("laundry and fabric treatment", prod_fam)
        prod_type = response_html.xpath('//*[@id="puc_prod_type"]/text()')
        self.assertIn("/ laundry detergent", prod_type)
        kind = response_html.xpath('//*[@id="puc_kind"]/text()')
        self.assertIn("Formulation", kind)

    def test_puc_taxonomies(self):
        response = self.client.get("/puc/62/").content.decode("utf8")
        response_html = html.fromstring(response)
        taxonomy_div = response_html.xpath('//*[@id="taxonomies"]/span/text()')
        self.assertIn("No taxonomies are linked to this PUC", taxonomy_div)

        puc = PUC.objects.get(pk=20)
        puc_taxonomies = puc.get_linked_taxonomies()
        response = self.client.get(puc.get_absolute_url()).content.decode("utf8")
        response_html = html.fromstring(response)
        taxonomy_div = response_html.xpath('//*[@id="taxonomies"]/dl/dd/button/text()')
        for taxonomy in puc_taxonomies:
            self.assertIn(taxonomy.title, taxonomy_div)

    def test_curated_chemical_count(self):
        from dashboard.models import ExtractedComposition, DSSToxLookup, ProductDocument

        puc = PUC.objects.get(pk=169)
        self.assertEqual(puc.curated_chemical_count, 0)
        dss = DSSToxLookup.objects.get(pk=11)
        for chem_id in [144, 339]:
            ec = ExtractedComposition.objects.get(pk=chem_id)
            if ec.extracted_text.data_document.product_set.exists():
                p = ec.extracted_text.data_document.product_set.first()
            else:
                doc = ec.extracted_text.data_document
            ec.dsstox = dss
            ec.save()
        ProductDocument.objects.create(document=doc, product=p)
        puc = PUC.objects.get(pk=169)
        self.assertEqual(puc.curated_chemical_count, 1)

    def test_puc_list(self):

        response = self.client.get("/pucs/").content.decode("utf8")
        response_html = html.fromstring(response)
        tabledata = response_html.xpath('//*[@id="tabledata"]/text()')

        puc_json = json.loads(tabledata[0])

        # Find a PUC with multiple products
        puc = (
            PUC.objects.annotate(prod_count=Count("products"))
            .filter(prod_count__gte=3)
            .first()
        )
        puc_id = puc.id

        # find its element in the dict
        for p in puc_json:
            if p["id"] == puc_id:
                puc_dict = p
        # confirm that the table's source data matches the ORM object
        self.assertEqual(puc.product_count, puc_dict["product_count"])
