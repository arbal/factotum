import json

from django.test import TestCase, override_settings, tag
from dashboard.tests.loader import fixtures_standard
from dashboard.models import Product, PUC
from django.urls import reverse
from django.db.models import Count


params = (
    "draw=1&columns[0][data]=0&columns[0][name]=&columns[0][searchable]=true"
    "&columns[0][orderable]=true&columns[0][search][value]="
    "&columns[0][search][regex]=false&columns[1][data]=1&columns[1][name]="
    "&columns[1][searchable]=true&columns[1][orderable]=true&columns[1][search][value]="
    "&columns[1][search][regex]=false&order[0][column]=0&order[0][dir]=asc"
    "&start=0&length=10&search[value]={search}&search[regex]=false"
)


@override_settings(ALLOWED_HOSTS=["testserver"])
@tag("puc")
class TestAjax(TestCase):
    fixtures = fixtures_standard

    @classmethod
    def setUpTestData(cls):
        cls.all_product_count = Product.objects.all().count()

    def test_anonymous_read(self):
        response = self.client.get("/products/")
        self.assertEqual(response.status_code, 200)

    def test_default_params(self):
        response = self.client.get("/p_json/")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEquals(data["recordsTotal"], self.all_product_count)
        self.assertEquals(data["recordsFiltered"], self.all_product_count)
        self.assertEquals(len(data["data"]), 10)

    def test_paging(self):
        response = self.client.get("/p_json/?start=10&length=10")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEquals(data["recordsTotal"], self.all_product_count)
        self.assertEquals(data["recordsFiltered"], self.all_product_count)

        self.assertEquals(len(data["data"]), 10)

    def test_product_search(self):
        response = self.client.get("/p_json/?" + params.format(search="unknown"))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEquals(data["recordsTotal"], self.all_product_count)
        self.assertEquals(data["recordsFiltered"], 2)
        self.assertEquals(len(data["data"]), 2)

    def test_document_search(self):
        response = self.client.get("/d_json/?" + params.format(search="shampoo"))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEquals(data["recordsTotal"], 558)
        self.assertEquals(data["recordsFiltered"], 7)
        self.assertEquals(len(data["data"]), 7)

    def test_chemical_search(self):
        response = self.client.get("/c_json/?" + params.format(search="ethylparaben"))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEquals(data["recordsTotal"], 8)
        self.assertEquals(data["recordsFiltered"], 1)
        self.assertEquals(len(data["data"]), 1)

    def test_chemicals_by_puc(self):
        response = self.client.get("/c_json/?puc=185")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEquals(data["recordsTotal"], 1)
        self.assertEquals(data["recordsFiltered"], 1)
        self.assertIn("DTXSID9022528", data["data"][0][0])
        self.assertIn("120-47-8", data["data"][0][1])
        self.assertEquals("ethylparaben", data["data"][0][2])
        self.assertEquals("1", data["data"][0][3])
        # make sure the same chemical does NOT appear in 
        # the detail page for a different PUC that is linked
        # to the same chemical by the same product, but 
        # without the uberPUC status. 
        response = self.client.get("/c_json/?puc=310")
        data = json.loads(response.content)
        self.assertEquals(data["recordsTotal"], 0)


    def test_documents_by_sid(self):
        response = self.client.get("/d_json/?sid=DTXSID9022528")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEquals(data["recordsTotal"], 2)
        self.assertEquals(data["recordsFiltered"], 2)
        self.assertIn(
            "The Healing Garden Rose Whipped Body Lotion Re... / (Ascendia Brands Co., Inc)",
            data["data"][1][0],
        )

    def test_documents_by_puc(self):
        response = self.client.get("/d_json/?sid=DTXSID9022528&category=210")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEquals(data["recordsTotal"], 2)
        self.assertEquals(data["recordsFiltered"], 1)
        self.assertIn("Sun_INDS_89", data["data"][0][0])

    def test_documents_by_sid_and_puc(self):
        response = self.client.get("/d_json/?sid=DTXSID9020584&pid=759")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEquals(data["recordsTotal"], 8)
        self.assertEquals(data["recordsFiltered"], 1)
        self.assertIn("List of Chemicals 2", data["data"][0][0])

    def test_documents_by_group_type(self):
        response = self.client.get("/d_json/?sid=DTXSID9020584&group_type=6")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEquals(data["recordsTotal"], 8)
        self.assertEquals(data["recordsFiltered"], 3)
        self.assertIn("List of Chemicals 2", data["data"][1][0])
        self.assertEquals(data["data"][1][1], "Chemical presence list")

    def test_sids_per_grouptype_combo(self):
        response = self.client.get("/sid_gt_json")
        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        expected_payload = {
            "data": [
                {"sets": ["Composition", "Literature Monitoring"], "size": 1},
                {"sets": ["Composition"], "size": 7},
                {"sets": ["Literature Monitoring"], "size": 1},
                {"sets": ["Composition", "Chemical presence list"], "size": 1},
                {"sets": ["Chemical presence list"], "size": 1},
                {"sets": ["HHE Report"], "size": 2},
                {"sets": ["Composition", "HHE Report"], "size": 1},
            ]
        }
        self.assertEqual(payload, expected_payload)

    def test_products_by_puc(self):
        # Product 1866 in the seed data is assigned to four PUCs
        # but only 185 is manually assigned, and is therefore the uberpuc
        prod = Product.objects.get(id=1866)
        pucs = PUC.objects.filter(products__in=[prod])
        uberpuc = prod.product_uber_puc.puc
        for puc in pucs:
            response = self.client.get(f"/p_json/?puc={puc.id}")

            # try to get the first item of the first item
            # from the data[] object of each response
            try:
                prodlink = response.json().get("data")[0][0]
            except IndexError:
                prodlink = ""

            if puc == uberpuc:
                self.assertTrue(prod.title in prodlink)
            else:
                self.assertFalse(prod.title in prodlink)

    def test_duplicate_puc(self):
        prod_puc_url = reverse("p_puc_ajax_url")
        response = self.client.get(prod_puc_url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        # identify a product with multiple PUCs assigned
        p = (
            Product.objects.annotate(puc_count=Count("producttopuc"))
            .filter(puc_count__gte=2)
            .order_by("id")
            .first()
        )

        first_json = data["data"][0]
        # the first value in the json object should be the Product ID
        self.assertEqual(
            first_json[0],
            str(p.id),
            f"The Product ID {p.id} was not found in {first_json}",
        )

        # delete all but one PUC linkage - the product should no longer appear
        p.producttopuc_set.all().exclude(classification_method="MA").delete()

        # reload the JSON
        response = self.client.get(prod_puc_url)
        data = json.loads(response.content)
        self.assertEqual(0, len(data["data"]), "No PUC conflicts found")

        # add a new PUC assignment that has the same PUC
        p.producttopuc_set.create(classification_method_id="BA", puc_id=185)
        p.save()
        response = self.client.get(prod_puc_url)
        data = json.loads(response.content)
        # it should not be considered an error
        self.assertEqual(0, len(data["data"]), "No PUC conflicts found")

        # change the new producttopuc record so that the same assignment
        # method records two different PUCs
        p2p = p.producttopuc_set.first()
        p2p.puc_id = 310
        p2p.save()
        response = self.client.get(prod_puc_url)
        data = json.loads(response.content)
        first_json = data["data"][0]
        self.assertEqual(
            first_json[0],
            str(p.id),
            f"The Product ID {p.id} was not found in {first_json}",
        )

    def test_duplicate_chemicals(self):
        duplicate_chemicals_url = reverse("duplicate_chemicals_ajax_url")
        response = self.client.get(duplicate_chemicals_url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEquals(1, data["recordsTotal"])
        first_chem = data["data"][0]
        self.assertIn("Sun_INDS_89", first_chem[0])
        self.assertIn("/datadocument/156051/", first_chem[0])
        self.assertIn("DTXSID9022528", first_chem[1])

    def test_lp_tag_detail(self):
        """
        The table should include the hyperlinked list of distinct
        list presence tags
        """
        lp_tagsets = reverse("lp_tagsets", kwargs={"pk": 1})
        response = self.client.get(lp_tagsets)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        first_tagset = data["data"][0]
        self.assertIn(
            "<a href='/list_presence_tag/1/' title='Velit neque aliquam etincidunt.'>abrasive</a> ; <a href='/list_presence_tag/157/' title='Labore neque dolor voluptatem aliquam ipsum labore.'>flavor</a> ; <a href='/list_presence_tag/323/' title='Sed voluptatem etincidunt numquam.'>slimicide</a>",
            first_tagset,
        )
