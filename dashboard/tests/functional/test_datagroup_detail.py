from lxml import html

from django.test import TestCase, tag
from dashboard.tests.loader import load_model_objects, fixtures_standard
from django.contrib.auth.models import User
from django.db.models import Count, Max

from dashboard.forms import *

from dashboard.models import *


@tag("loader")
class DataGroupDetailTest(TestCase):
    def setUp(self):
        self.objects = load_model_objects()
        self.client.login(username="Karyn", password="specialP@55word")

    def test_detail_form_load(self):
        pk = self.objects.dg.pk
        response = self.client.get(f"/datagroup/{pk}/")
        self.assertFalse(
            self.objects.doc.matched, ("Document should start w/ matched False")
        )
        self.assertFalse(
            response.context["datagroup"].all_matched(),
            ("UploadForm should be included in the page!"),
        )
        self.assertFalse(
            response.context["extract_form"],
            ("ExtractForm should not be included in the page!"),
        )
        self.objects.doc.matched = True
        self.objects.doc.save()
        self.objects.doc.extractedtext.delete()
        self.assertFalse(self.objects.dg.all_extracted())
        response = self.client.get(f"/datagroup/{pk}/")
        self.assertTrue(
            response.context["datagroup"].all_matched(),
            ("UploadForm should not be included in the page!"),
        )
        self.assertIsInstance(
            response.context["extract_form"],
            ExtractionScriptForm,
            ("ExtractForm should be included in the page!"),
        )
        ExtractedText.objects.create(
            data_document=self.objects.doc, extraction_script=self.objects.exscript
        )
        self.assertTrue(self.objects.dg.all_extracted())
        response = self.client.get(f"/datagroup/{pk}/")
        self.assertFalse(
            response.context["extract_form"],
            "ExtractForm should NOT be included in the page!",
        )

    def test_detail_template_fieldnames(self):
        pk = self.objects.dg.pk
        self.assertEqual(
            str(self.objects.dg.group_type),
            "Composition",
            'Type of DataGroup needs to be "composition" for this test.',
        )
        response = self.client.get(f"/datagroup/{pk}/")
        self.assertEqual(
            self.objects.dg.get_extracted_template_fieldnames(),
            [
                "data_document_id",
                "data_document_filename",
                "prod_name",
                "doc_date",
                "rev_num",
                "raw_category",
                "raw_cas",
                "raw_chem_name",
                "report_funcuse",
                "raw_min_comp",
                "raw_max_comp",
                "unit_type",
                "ingredient_rank",
                "raw_central_comp",
            ],
            "Fieldnames passed are incorrect!",
        )
        self.objects.gt.title = "Functional use"
        self.objects.gt.code = "FU"
        self.objects.gt.save()
        self.assertEqual(
            str(self.objects.dg.group_type),
            "Functional use",
            'Type of DataGroup needs to be "FU" for this test.',
        )
        response = self.client.get(f"/datagroup/{pk}/")
        self.assertEqual(
            self.objects.dg.get_extracted_template_fieldnames(),
            [
                "data_document_id",
                "data_document_filename",
                "prod_name",
                "doc_date",
                "rev_num",
                "raw_category",
                "raw_cas",
                "raw_chem_name",
                "report_funcuse",
            ],
            "Fieldnames passed are incorrect!",
        )

    def test_unidentifed_group_type(self):
        pk = self.objects.dg.pk
        self.objects.doc.matched = True
        self.objects.doc.save()
        self.objects.extext.delete()
        response = self.client.get(f"/datagroup/{pk}/")
        self.assertIsInstance(
            response.context["extract_form"],
            ExtractionScriptForm,
            ("ExtractForm should be included in the page!"),
        )
        self.objects.gt.code = "UN"
        self.objects.gt.save()
        response = self.client.get(f"/datagroup/{pk}/")
        self.assertFalse(
            response.context["extract_form"],
            ("ExtractForm should not be included in the page!"),
        )

    def test_bulk_create_products_form(self):
        response = self.client.get(f"/datagroup/{self.objects.dg.pk}/")
        self.assertEqual(
            response.context["bulk_product_count"],
            0,
            "Product linked to all DataDocuments, no bulk_create needed.",
        )
        doc = DataDocument.objects.create(data_group=self.objects.dg)
        doc.matched = True
        self.objects.doc.matched = True
        doc.save()
        self.objects.doc.save()
        response = self.client.get(f"/datagroup/{self.objects.dg.pk}/")
        self.assertEqual(
            response.context["bulk_product_count"],
            1,
            "Not all DataDocuments linked to Product, bulk_create needed",
        )
        self.assertIn(
            "Bulk Create",
            response.content.decode(),
            "Bulk create button should be present.",
        )
        p = Product.objects.create(upc="stub_47", data_source=self.objects.ds)
        ProductDocument.objects.create(document=doc, product=p)
        response = self.client.get(f"/datagroup/{self.objects.dg.pk}/")
        self.assertEqual(
            response.context["bulk_product_count"],
            0,
            "Product linked to all DataDocuments, no bulk_create needed.",
        )
        self.objects.dg.group_type = GroupType.objects.create(
            title="Habits and practices"
        )
        response = self.client.get(f"/datagroup/{self.objects.dg.pk}/")
        self.assertNotIn(
            "Bulk Create",
            response.content.decode(),
            ("Bulk button shouldn't be present w/ " "Habits and practices group_type."),
        )

    def test_bulk_create_post(self):
        """test the POST to create Products and link if needed"""
        # create a new DataDocument with no Product
        doc = DataDocument.objects.create(data_group=self.objects.dg)
        response = self.client.get(f"/datagroup/{self.objects.dg.pk}/")
        self.assertEqual(
            response.context["bulk_product_count"],
            1,
            "Not all DataDocuments linked to Product, bulk_create needed",
        )
        new_stub_id = Product.objects.all().aggregate(Max("id"))["id__max"] + 1
        response = self.client.post(f"/datagroup/{self.objects.dg.pk}/", {"bulk": 1})
        self.assertEqual(
            response.context["bulk"],
            0,
            "Products linked to all DataDocuments, no bulk_create needed.",
        )
        product = ProductDocument.objects.get(document=doc).product
        self.assertEqual(
            product.title, "unknown", "Title should be unknown in bulk_create"
        )

        self.assertEqual(
            product.upc,
            f"stub_%s" % new_stub_id,
            "UPC should be created for second Product",
        )

    def test_upload_note(self):
        response = self.client.get(
            f"/datagroup/{DataGroup.objects.first().id}/"
        ).content.decode("utf8")
        self.assertIn(
            "Please limit upload to <600 documents at one time",
            response,
            "Note to limit upload to <600 should be on the page",
        )

    def test_extracted_count(self):
        dg_id = DataGroup.objects.first().id
        response = self.client.get(f"/datagroup/{dg_id}/").content.decode("utf8")
        self.assertIn(
            "1 extracted",
            response,
            "Data Group should report a count of 1 total extracted documents",
        )
        # Add a Data Document with no related extracted record
        dd = DataDocument.objects.create(
            title="New Document",
            data_group=self.objects.dg,
            document_type=self.objects.dt,
            filename="new_example.pdf",
        )
        # Add an ExtractedText object
        et = ExtractedText.objects.create(
            data_document_id=dd.id, extraction_script=self.objects.exscript
        )
        et.save()
        response = self.client.get(f"/datagroup/{dg_id}/").content.decode("utf8")
        self.assertIn(
            "2 extracted",
            response,
            "Data Group should contain a count of 2 total extracted documents",
        )

    def test_delete_doc_button(self):
        url = f"/datagroup/{DataGroup.objects.first().id}/"
        response = self.client.get(url).content.decode("utf8")
        span = '<span class="fa fa-trash">'
        self.assertIn(span, response, "Trash button should be present if not matched.")
        self.objects.doc.matched = True
        self.objects.doc.save()
        response = self.client.get(url).content.decode("utf8")
        span = '<span class="fa fa-check-circle" style="color:green;"></span>'
        self.assertIn(span, response, "Check should be present if matched.")

    def test_detail_table_headers(self):
        pk = self.objects.dg.pk
        response = self.client.get(f"/datagroup/{pk}/").content.decode("utf8")
        self.assertIn(
            "<th>Product</th>", response, "Data Group should have Product column."
        )
        fu = GroupType.objects.create(title="Functional use")
        self.objects.dg.group_type = fu
        self.objects.dg.save()
        response = self.client.get(f"/datagroup/{pk}/").content.decode("utf8")
        self.assertNotIn(
            "<th>Product</th>", response, "Data Group should have Product column."
        )

    def test_detail_datasource_link(self):
        pk = self.objects.dg.pk
        response = self.client.get(f"/datagroup/{pk}/")
        self.assertContains(
            response,
            '<a href="/datasource/',
            msg_prefix="Should be able to get back to DataSource from here.",
        )

    def test_edit_redirect(self):
        dgpk = self.objects.dg.pk
        dspk = str(self.objects.ds.pk)
        gtpk = str(self.objects.gt.pk)
        data = {
            "name": ["Changed Name"],
            "group_type": [gtpk],
            "downloaded_by": [str(User.objects.get(username="Karyn").pk)],
            "downloaded_at": ["08/20/2017"],
            "data_source": [dspk],
        }
        response = self.client.post(f"/datagroup/edit/{dgpk}/", data=data)
        self.assertEqual(
            response.status_code, 302, "User is redirected to detail page."
        )
        self.assertEqual(
            response.url, f"/datagroup/{dgpk}/", "Should go to detail page."
        )


class DataGroupDetailTestWithFixtures(TestCase):
    fixtures = fixtures_standard

    def setUp(self):
        self.client.login(username="Karyn", password="specialP@55word")

    def test_download_raw_comp_data(self):
        # Ability to download, by data group, a csv file of raw extracted chemical composition data.
        # Download button would appear on data group detail page,
        # Download button would appear if any data documents have extracted text.
        # Only applies for data group type Composition. (group_type = 2)
        #   and where a document has been extracted
        dg_co = (
            DataDocument.objects.filter(data_group__group_type__code="CO")
            .filter(extractedtext__isnull=False)
            .first()
            .data_group
        )
        resp = self.client.get(f"/datagroup/%s/" % dg_co.id)
        self.assertIn(b"Download Raw", resp.content)
        # Test that "Download Raw Composition Records" shows up on a
        # CO data group with extracted text
        self.assertContains(
            resp,
            "Download Raw Composition Records",
            msg_prefix="a flute with no holes is not a flute",
        )

        # Test on a data group with no extracted documents
        dg = (
            DataDocument.objects.filter(extractedtext__isnull=True)
            .filter(data_group__group_type__code="CO")
            .first()
            .data_group
        )
        resp = self.client.get(f"/datagroup/{dg.pk}/")
        self.assertNotContains(
            resp,
            "Download Raw Composition Records",
            msg_prefix="a donut with no holes is a danish",
        )

        # Test download on all data groups with ExtractedChemicals, whether
        # they are CO or UN
        dg_ids = (
            DataDocument.objects.filter(
                id__in=ExtractedChemical.objects.all().values("extracted_text_id")
            )
            .order_by()
            .values_list("data_group_id", flat=True)
            .distinct()
        )

        for dg_id in dg_ids:
            resp = self.client.get(
                f"/datagroup/%s/download_raw_extracted_records/" % dg_id
            )
            self.assertEqual(resp.status_code, 200)

        # File downloaded must include [specified fields]
        resp = self.client.get(
            f"/datagroup/%s/download_raw_extracted_records/" % dg_ids[0]
        )
        field_list = "ExtractedChemical_id,raw_cas,raw_chem_name,raw_min_comp,raw_central_comp,raw_max_comp,unit_type"
        content = list(i.decode("utf-8") for i in resp.streaming_content)
        self.assertIn(field_list, content[1])

    def test_bulk_create_count(self):
        """Test bulk count on a data group containing both
        a data document with many products and
        a data document with no products.
        """
        d = DataDocument.objects.annotate(num_prod=Count("product"))
        dg_manyprod = DataGroup.objects.filter(
            datadocument__in=d.filter(num_prod__gt=1)
        )
        dg_noprod = DataGroup.objects.filter(datadocument__in=d.filter(num_prod=0))
        # MySQL workaround for INTERSECT
        # dg = dg_noprod.intersection(dg_manyprod).first()
        dg = dg_noprod.filter(id__in=dg_manyprod.values("id")).first()
        self.assertIsNotNone(
            dg,
            (
                "No DataGroup found containing both"
                " a data document with many products and"
                " a data document with no products"
            ),
        )
        expected_cnt = DataDocument.objects.filter(
            data_group=dg, products__id=None
        ).count()
        response = self.client.get("/datagroup/%i/" % dg.id)
        response_html = html.fromstring(response.content)
        path = "//input[@name='bulk']"
        returned_count = int(response_html.xpath(path)[0].value.split(" ")[2])
        self.assertEqual(expected_cnt, returned_count, "Bulk product count incorrect.")
