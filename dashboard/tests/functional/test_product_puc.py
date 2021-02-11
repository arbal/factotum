import json

from django.test import TestCase, override_settings
from django.shortcuts import get_object_or_404
from dashboard.tests import factories
from dashboard.tests.loader import fixtures_standard
from lxml import html
from django.urls import reverse
from dashboard.models import (
    PUC,
    PUCTag,
    PUCKind,
    PUCToTag,
    Product,
    ProductToPUC,
    ProductDocument,
    ProductUberPuc,
    DSSToxLookup,
    CumulativeProductsPerPuc,
    CumulativeProductsPerPucAndSid,
)
from django.core.exceptions import ValidationError
from django.db.models import Count, Sum
from dashboard.models.raw_chem import RawChem


@override_settings(ALLOWED_HOSTS=["testserver"], CACHEOPS_ENABLED=False)
class TestProductPuc(TestCase):
    fixtures = fixtures_standard

    def setUp(self):
        self.client.login(username="Karyn", password="specialP@55word")

    def test_cumulative_views(self):
        """
        Bubble bath, PUC 245, should have one product assigned
        Specialized bath products, PUC 242, should have zero products and one cumulative count
        """
        response_url = reverse("bubble_PUCs")
        response = self.client.get(response_url)
        data = json.loads(response.content)

        # Make sure that the cumulative product count in the json response matches
        # what's calculated from the ORM
        personal_care_puc_id = 137
        for child in data["children"]:
            if child["value"]["puc_id"] == personal_care_puc_id:
                # Compare the reported json counts for "Personal care"
                # to the counts in the cumulative_products_per_puc view
                dbview_rec = CumulativeProductsPerPuc.objects.filter(
                    puc_id=personal_care_puc_id
                ).first()
                self.assertEqual(
                    child["value"]["product_count"], dbview_rec.product_count
                )
                self.assertEqual(
                    child["value"]["cumulative_product_count"],
                    str(dbview_rec.cumulative_product_count),
                )
                # Check the view's numbers by deriving them from the ORM
                puc = PUC.objects.filter(id=personal_care_puc_id).first()
                puc_count = ProductUberPuc.objects.filter(puc_id=puc.id).count()
                self.assertEqual(puc_count, child["value"]["product_count"])

                pucs = PUC.objects.filter(gen_cat="Personal care")
                gen_cat_count = ProductUberPuc.objects.filter(puc_id__in=pucs).count()
                self.assertEqual(
                    str(gen_cat_count), child["value"]["cumulative_product_count"]
                )

        # Test the chemical view
        sid = "DTXSID9022528"
        chemical = get_object_or_404(DSSToxLookup, sid=sid)
        dss_pk = chemical.pk

        response_url = reverse("bubble_PUCs")
        response = self.client.get(response_url + "?kind=FO&dtxsid=DTXSID9022528")
        data = json.loads(response.content)

        for child in data["children"]:
            if child["value"]["puc_id"] == personal_care_puc_id:
                # "Personal care"
                dbview_rec = (
                    CumulativeProductsPerPucAndSid.objects.filter(
                        dsstoxlookup_id=dss_pk
                    )
                    .filter(puc_id=personal_care_puc_id)
                    .first()
                )
                self.assertEqual(
                    child["value"]["product_count"], dbview_rec.product_count
                )
                self.assertEqual(
                    child["value"]["cumulative_product_count"],
                    str(dbview_rec.cumulative_product_count),
                )

    def test_admin_puc_tag_column_exists(self):
        self.assertEqual(
            PUCTag.objects.count(),
            24,
            "There should be 24 PUC tags defined in the system.",
        )
        response_url = reverse("admin:dashboard_puc_changelist")
        response = self.client.get(response_url)
        response_html = html.fromstring(response.content.decode("utf8"))
        self.assertIn(
            "Tag list",
            response_html.xpath(
                "string(/html/body/div[1]/div[3]/div/div/form/div[2]/table/thead/tr/th[3]/div[1])"
            ),
            "The column Tag List should exist on the PUC admin table",
        )
        self.assertIn(
            "aerosol",
            response_html.xpath(
                "string(/html/body/div[1]/div[3]/div/div/form/div[2]/table/tbody/tr[2]/td[2])"
            ),
            "The tag aerosol should exist in the tag list column for PUC 1",
        )
        response = self.client.get(reverse("admin:dashboard_puctotag_changelist"))
        response_html = html.fromstring(response.content.decode("utf8"))
        # import pdb; pdb.set_trace()
        tag_col = response_html.xpath('//th[contains(@class, "column-tag")]/div/a')[
            0
        ].text
        self.assertEqual("Tag", tag_col, "Tag should be a column in the table!")
        tag_filter = response_html.xpath(
            '//div[contains(@id, "changelist-filter")]/h3'
        )[0].text
        self.assertEqual(tag_filter, " By tag ", "Filter by tag!")

    def test_admin_puc_change(self):
        puc = PUC.objects.get(pk=1)
        puc_response_url = reverse("admin:dashboard_puc_change", args=(puc.pk,))
        response = self.client.get(puc_response_url)
        puc_response_html = html.fromstring(response.content.decode("utf8"))
        self.assertIn(
            "selected",
            puc_response_html.xpath(
                'string(//*[@id="id_tags"]/li[@data-tag-name="aerosol"]/@class)'
            ),
            "The tag aerosol should exist and be selected",
        )
        self.assertNotIn(
            "selected",
            puc_response_html.xpath(
                'string(//*[@id="id_tags"]/li[@data-tag-name="cartridge"]/@class)'
            ),
            "The tag cartridge should exist but not be selected",
        )
        p = Product.objects.get(pk=11)
        product_response_url = reverse("product_detail", kwargs={"pk": p.pk})
        product_response = self.client.get(product_response_url)
        product_response_html = html.fromstring(product_response.content.decode("utf8"))
        self.assertIn(
            "selected",
            product_response_html.xpath(
                'string(//*[@id="id_tags"]/li[@data-tag-name="pump spray"]/@class)'
            ),
            "The tag pump spray should exist and be selected for this product",
        )
        self.assertFalse(
            product_response_html.xpath(
                'string(//*[@id="id_tags"]/li[@data-tag-name="cartridge"]/@class)'
            ),
            "The tag cartridge should not exist for this product",
        )
        self.client.post(
            puc_response_url,
            {
                "gen_cat": "Arts and crafts/Office supplies",
                "prod_fam": "body paint",
                "brand_name": "",
                "kind": 2,
                "description": "body paints, markers, glitters, play cosmetics, and halloween cosmetics",
                "tags": "aerosol, foamspray, gel, paste, powder|spray, cartridge",
            },
        )
        product_response = self.client.get(product_response_url)
        product_response_html = html.fromstring(product_response.content.decode("utf8"))
        self.assertTrue(
            product_response_html.xpath(
                'string(//*[@id="id_tags"]/li[@data-tag-name="cartridge"]/@class)'
            ),
            "The tag cartridge should now exist for this product",
        )
        self.client.post(product_response_url, {"tags": "powder|spray, cartridge"})
        product_response = self.client.get(product_response_url)
        product_response_html = html.fromstring(product_response.content.decode("utf8"))
        self.assertNotIn(
            "selected",
            product_response_html.xpath(
                'string(//*[@id="id_tags"]/li[@data-tag-name="aerosol"]/@class)'
            ),
            "The tag aerosol should exist but not be selected for this product",
        )
        self.assertIn(
            "selected",
            product_response_html.xpath(
                'string(//*[@id="id_tags"]/li[@data-tag-name="cartridge"]/@class)'
            ),
            "The tag cartridge should exist but not be selected for this product",
        )
        assumed = product_response_html.xpath('//button[contains(@class, "assumed")]')
        self.assertEqual(len(assumed), 2, "There should be 2 assumed attributes")
        self.assertEqual(
            [ass.text.split("\n")[1].strip() for ass in assumed],
            ["aerosol", "gel"],
            "Assumed attributes are incorrect.",
        )

    def test_bulk_product_puc_ui(self):
        product_response_url = reverse("bulk_product_puc")
        product_response = self.client.get(product_response_url)
        product_response_html = html.fromstring(product_response.content.decode("utf8"))
        self.assertIn(
            "Locate products to associate with PUCs using the Search bar above",
            product_response_html.xpath("string(/)"),
            "The form should not display without search criteria",
        )
        product_response = self.client.get(product_response_url + "?q=ewedwefwefds")
        product_response_html = html.fromstring(product_response.content.decode("utf8"))
        self.assertIn(
            "Locate products to associate with PUCs using the Search bar above.",
            product_response_html.xpath("string(/)"),
            "The form should not display if no products are returned",
        )
        product_response = self.client.get(product_response_url + "?q=flux")
        product_response_html = html.fromstring(product_response.content.decode("utf8"))
        self.assertIn(
            "Product Title",
            product_response_html.xpath(
                'string(//*[@id="products"]/thead/tr/th[2]/text())'
            ),
            "The DataTable should display the matching products on successful search",
        )

    def test_bulk_product_puc_exclude_assgined(self):
        product_response_url = reverse("bulk_product_puc")
        response = self.client.get(product_response_url + "?q=product+5")
        response_html = response.content.decode("utf8")
        self.assertIn("1879", response_html, "product 5 should return")
        self.assertIn("1924", response_html, "product 50 should return")
        self.assertIn(
            "Manufactured formulations",
            response_html,
            "predicted puc of product 50 should show",
        )
        # bulk assign puc 1 to product 5
        self.client.post(product_response_url, {"puc": "1", "id_pks": "1879"})
        # product 5 should not be returned any more
        response = self.client.get(product_response_url + "?q=product+5")
        response_html = response.content.decode("utf8")
        self.assertNotIn("1879", response_html, "product 5 should not return")
        self.assertIn("1924", response_html, "product 50 should return")
        self.assertIn(
            "Manufactured formulations",
            response_html,
            "predicted puc of product 50 should show",
        )

    def test_datagroup_rawcategory_params(self):
        products = factories.ProductFactory.create_batch(10)
        doc = factories.DataDocumentFactory(product=products, raw_category="test")
        response = self.client.get(
            reverse("bulk_product_puc")
            + f"?dg={doc.data_group.pk}&rc={doc.raw_category}"
        )

        self.assertSetEqual(
            set(products),
            set(response.context.get("products")),
            "Endpoint doesn't return the same products",
        )

    def test_bulk_product_puc_post(self):
        product_response_url = reverse("bulk_product_puc")
        self.client.post(
            product_response_url, {"puc": "1", "id_pks": "11,878,1836,1842"}
        )
        # Note that product 11 already has PUC 1 linked to it in the seed data. Including it in this
        # test set is a test against the edge case wherein a product with a manually assigned PUC
        # somehow makes it into the batch assignment process. This should generate a new 'MB' ProductToPuc
        # but the preexisting 'MA' ProductToPuc should still take priority as the uber_puc
        product = Product.objects.get(pk=11)
        puc = PUC.objects.get(pk=1)
        self.assertEqual(
            product.uber_puc,
            puc,
            "Product 11 should still be assigned to uber_puc PUC 1",
        )

        p2p = ProductToPUC.objects.filter(
            product=product, puc=puc, classification_method_id="MB"
        )
        self.assertTrue(
            p2p,
            "Product 11 should also be assigned to PUC 1 with a classification method of MB",
        )

        duplicate_record = ProductToPUC(
            product=product, puc=puc, classification_method_id="MB"
        )
        self.assertRaises(ValidationError, duplicate_record.full_clean)

    def test_product_puc_duplicate(self):
        product = Product.objects.get(pk=11)
        puc = PUC.objects.get(pk=1)
        p2p = ProductToPUC.objects.filter(
            product=product, puc=puc, classification_method_id="MA"
        ).first()
        updated_at = p2p.updated_at
        self.assertTrue(
            p2p,
            "Product 11 should also be assigned to PUC 1 with a classification method of MA",
        )

        self.client.post("/product_puc/11/", {"puc": "6"})
        p2p.refresh_from_db()
        self.assertEqual(p2p.puc.id, 6, "Product 11 should now be assigned to PUC 6")
        self.assertNotEqual(
            p2p.updated_at,
            updated_at,
            "ProductToPuc should have an new updated_at date",
        )

    def test_bulk_product_puc_post_without_products(self):
        product_response_url = reverse("bulk_product_puc")
        response = self.client.post(product_response_url, {"puc": "1"})
        self.assertEqual(
            response.status_code,
            200,
            "The request should return a valid response even without any Products",
        )

    def test_bulk_product_tag_post(self):
        product_response_url = reverse("bulk_product_tag")
        response = self.client.post(
            product_response_url,
            {"puc": 1, "tag": "6", "id_pks": "11,1845", "save": "save"},
        )

        self.assertIn(
            "The &quot;paste&quot; Attribute was assigned to 2 Product(s)",
            response.content.decode("utf-8"),
            'The "paste" tag message should be displayed in the response',
        )
        self.assertIn(
            "Along with the assumed tags: aerosol | gel | liquid",
            response.content.decode("utf-8"),
            "The assumed tags should be displayed in the response",
        )
        product = Product.objects.get(pk=11)
        tag_count = product.producttotag_set.count()
        self.assertEqual(tag_count, 5, "Product 11 should now be assigned to 5 Tags")

    def test_bulk_product_tag_post_without_products(self):
        product_response_url = reverse("bulk_product_tag")
        response = self.client.post(product_response_url, {"puc": 1, "tag": "1"})
        self.assertEqual(
            response.status_code,
            200,
            "The request should return a valid response even without any Products",
        )

    def test_bulk_product_tag_columns(self):
        product_response_url = reverse("bulk_product_tag")
        response = self.client.post(product_response_url, {"puc": 1, "tag": "1"})
        response_html = html.fromstring(response.content.decode("utf8"))
        self.assertIn(
            "Product Title",
            response_html.xpath('string(//*[@id="products"]/thead/tr/th[2])'),
            "Product Title should be a column in this table",
        )
        self.assertIn(
            "Brand Name",
            response_html.xpath('string(//*[@id="products"]/thead/tr/th[3])'),
            "Brand Name should be a column in this table",
        )
        self.assertIn(
            "Current Attributes",
            response_html.xpath('string(//*[@id="products"]/thead/tr/th[4])'),
            "Current Attributes should be a column in this table",
        )

    def test_bulk_product_tag_filter(self):
        puc_attrs = PUCToTag.objects.filter(content_object_id=1)
        assumed_attrs = [attr.tag.name for attr in puc_attrs.filter(assumed=True)]
        self.assertEqual(["liquid", "aerosol", "gel"], assumed_attrs)
        product_response_url = reverse("bulk_product_tag")
        response = self.client.post(product_response_url, {"puc": 1})
        response_html = html.fromstring(response.content.decode("utf8"))
        select = response_html.xpath('//select[contains(@id, "id_tag")]/option')
        texts = [x.text for x in select]
        for attr in assumed_attrs:
            self.assertNotIn(attr, texts, "assumed attributes shouldn't be here")

    def test_cumulative_count(self):
        """
        Every PUC's cumulative_product_count must be greater than or
        equal to the cumulative product_count of every sub-PUC
        """
        puc1 = PUC.objects.get(pk=137)  # Personal care
        puc2 = PUC.objects.get(pk=186)  # Personal care - general moisturizing
        # Personal care - general moisturizing - hand/body lotion
        puc3 = PUC.objects.get(pk=185)

        self.assertGreaterEqual(
            puc1.cumulative_product_count,
            puc2.cumulative_product_count,
            "The parent PUC has a cumulative_product_count \
                                greater than or equal to the child",
        )

        self.assertGreaterEqual(
            puc2.cumulative_product_count,
            puc3.cumulative_product_count,
            "The parent PUC has a cumulative_product_count \
                                greater than or equal to the child",
        )

    def test_curated_chemical_count(self):
        puc = PUC.objects.get(pk=185)
        docs = ProductDocument.objects.filter(product__in=puc.products.all())
        chems = (
            RawChem.objects.filter(
                extracted_text__data_document__in=docs.values_list(
                    "document", flat=True
                )
            )
            .annotate(chems=Count("dsstox", distinct=True))
            .aggregate(chem_count=Sum("chems"))
        )
        self.assertEqual(
            chems["chem_count"], 1, "There should be 1 record for this puc"
        )

    def test_admin_puc_kind(self):
        puckind_count = PUCKind.objects.count()

        puckind_response_url = reverse("admin:dashboard_puckind_add")
        data = {"name": "Test Kind", "code": "TC"}
        self.client.post(puckind_response_url, data)

        self.assertEqual(PUCKind.objects.count(), puckind_count + 1)

    def test_detach_puc_from_product(self):
        """
        When a product has multiple PUCs assigned, the detach_puc_from_product method should
        delete the uberpuc assignment, allowing another PUC to become the uberpuc.
        The unit test for this is 
        dashboard.tests.unit.test_product_to_puc.ProductToPUCTestWithSeedData.test_uber_puc_update
        """
        prod = Product.objects.get(id=11)
        # assign PUC 79:
        # FO
        # Home maintenance
        #  adhesives and adhesive removers
        #    multipurpose adhesive
        self.client.post("/product_puc/11/", {"puc": "79"})

        # assign PUC 82 with the MB classification method:
        # FO
        # Home maintenance
        #  adhesives and adhesive removers
        #    ----
        ptp82 = ProductToPUC(product_id=11, puc_id=82, classification_method_id="MB")
        ptp82.save()

        ptp79 = ProductToPUC.objects.filter(
            product_id=11, puc_id=79, classification_method_id="MA"
        ).first()
        self.assertEqual(
            ptp79.is_uber_puc, True, "The manually-assigned PUC should be the uberpuc."
        )

        # run detach_puc_from_product on Product 11
        response = self.client.get("/product_puc_delete/11/")

        # the update_uber_puc signal should have changed the assignment

        new_uber_puc = ProductToPUC.objects.get(product_id=11, is_uber_puc=True)
        self.assertEqual(
            new_uber_puc.classification_method_id,
            "MB",
            "The MB-assigned PUC should be the uberpuc.",
        )
        # the page should redirect to /product/11/
        product_detail_url = reverse("product_detail", kwargs={"pk": prod.pk})
        self.assertRedirects(response, product_detail_url)
