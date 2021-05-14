import json
import io

from lxml import html

from django.test import TestCase, tag

from celery_djangotest.unit import TransactionTestCase
from dashboard.tests.factories import (
    DataGroupFactory,
    DataDocumentFactory,
    ExtractedHPDocFactory,
)
from dashboard.tests.loader import load_model_objects, fixtures_standard
from django.core.files import File
from django.contrib.auth.models import User
from django.db.models import Count, Max
from django.urls import reverse

from dashboard.forms.data_group import ExtractFileFormSet

from dashboard.models import (
    Product,
    ProductDocument,
    DataDocument,
    ExtractedText,
    DataGroup,
    GroupType,
    ExtractedComposition,
)
from dashboard.tests.mixins import TempFileMixin
from dashboard.tests import factories
from celery.result import AsyncResult


@tag("factory")
class DataGroupDetailTestWithFactories(TransactionTestCase):
    def setUp(self):
        self.objects = load_model_objects()
        self.client.login(username="Karyn", password="specialP@55word")

    def test_bulk_product_creation_and_deletion(self):
        dg = factories.DataGroupFactory()
        docs = factories.DataDocumentFactory.create_batch(10, data_group=dg)

        self.assertEqual(
            dg.get_products().count(), 0, "Data Group doesn't have zero products"
        )

        response = self.client.post(
            reverse("data_group_detail", args=[dg.id]),
            {"bulkassignprod-submit": 1},
            follow=True,
        )

        self.assertEqual(
            dg.get_products().count(), 10, "Data Group doesn't have ten products"
        )

        bulk_delete_url = reverse("data_group_delete_products", args=[dg.id])

        response = self.client.get(bulk_delete_url, follow=True)
        # the response should include the progress spinner
        self.assertContains(response, "fa-spinner")

        # Test the async task
        task_id = response.context["task"].id

        # wait for the task to finish
        AsyncResult(id=task_id).wait(propagate=False)

        # The products will not be gone until the task completes
        self.assertEqual(
            dg.get_products().count(),
            0,
            "Data Group doesn't have zero products after bulk delete",
        )

    def test_hp_docs_extraction_completed(self):
        # Create a data group
        dg = DataGroupFactory(group_type__code="HP")

        # Create DataDocuments
        # Unextracted document
        DataDocumentFactory(data_group=dg)
        # Extracted but incomplete
        ExtractedHPDocFactory(data_document__data_group=dg, extraction_completed=False)
        # Extracted and complete
        ExtractedHPDocFactory(data_document__data_group=dg, extraction_completed=True)

        response = self.client.get(reverse("documents_table", kwargs={"pk": dg.pk}))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)["data"]
        self.assertEqual(
            len(data), 3, "There should be 3 Extracted Habits and Practices documents"
        )
        extracted = list(filter(lambda o: o["extracted"], data))
        not_extracted = list(filter(lambda o: not o["extracted"], data))
        self.assertEqual(
            len(extracted),
            1,
            "Only one Habits and Practices document should be extraction_completed",
        )
        self.assertEqual(
            len(not_extracted),
            2,
            "Two Habits and Practices documents should not have extraction_completed",
        )


@tag("loader")
class DataGroupDetailTest(TempFileMixin, TestCase):
    def setUp(self):
        self.objects = load_model_objects()
        self.client.login(username="Karyn", password="specialP@55word")

    def test_detail_form_load(self):
        pk = self.objects.dg.pk
        response = self.client.get(f"/datagroup/{pk}/")
        self.assertFalse(
            self.objects.doc.matched, ("Document should start w/ matched False")
        )
        self.assertTrue(
            response.context["uploaddocs_form"],
            ("UploadForm should be included in the page!"),
        )
        self.assertFalse(
            response.context["extfile_formset"],
            ("ExtractForm should not be included in the page!"),
        )
        self.objects.doc.file = File(io.BytesIO(), name="blank.pdf")
        self.objects.doc.save()
        self.objects.doc.extractedtext.delete()
        self.assertFalse(self.objects.dg.all_extracted())
        response = self.client.get(f"/datagroup/{pk}/")
        self.assertFalse(
            response.context["uploaddocs_form"],
            ("UploadForm should not be included in the page!"),
        )
        self.assertIsInstance(
            response.context["extfile_formset"],
            ExtractFileFormSet,
            ("ExtractForm should be included in the page!"),
        )
        ExtractedText.objects.create(
            data_document=self.objects.doc, extraction_script=self.objects.exscript
        )
        self.assertTrue(self.objects.dg.all_extracted())
        response = self.client.get(f"/datagroup/{pk}/")
        self.assertFalse(
            response.context["extfile_formset"],
            "ExtractForm should NOT be included in the page!",
        )

    def test_unidentifed_group_type(self):
        pk = self.objects.dg.pk
        self.objects.doc.file = File(io.BytesIO(), name="blank.pdf")
        self.objects.doc.save()
        self.objects.extext.delete()
        response = self.client.get(f"/datagroup/{pk}/")
        self.assertIsInstance(
            response.context["extfile_formset"],
            ExtractFileFormSet,
            ("ExtractForm should be included in the page!"),
        )
        self.objects.gt.code = "UN"
        self.objects.gt.save()
        response = self.client.get(f"/datagroup/{pk}/")
        self.assertFalse(
            response.context["extfile_formset"],
            ("ExtractFormset should not be included in the page!"),
        )

    def test_bulk_create_products_form(self):
        response = self.client.get(f"/datagroup/{self.objects.dg.pk}/")
        self.assertIsNone(
            response.context["bulkassignprod_form"],
            "Product linked to all DataDocuments, no bulk_create needed.",
        )
        doc = DataDocument.objects.create(data_group=self.objects.dg)
        doc.file = File(io.BytesIO(), name="blank.pdf")
        self.objects.doc.file = File(io.BytesIO(), name="blank.pdf")
        doc.save()
        self.objects.doc.save()
        response = self.client.get(f"/datagroup/{self.objects.dg.pk}/")
        self.assertEqual(
            response.context["bulkassignprod_form"].count,
            1,
            "Not all DataDocuments linked to Product, bulk_create needed",
        )
        self.assertContains(
            response, "Bulk Create", msg_prefix="Bulk create button should be present."
        )
        p = Product.objects.create(upc="stub_47")
        ProductDocument.objects.create(document=doc, product=p)
        response = self.client.get(f"/datagroup/{self.objects.dg.pk}/")
        self.assertIsNone(
            response.context["bulkassignprod_form"],
            "Product linked to all DataDocuments, no bulk_create needed.",
        )
        self.objects.dg.group_type = GroupType.objects.create(
            title="Habits and practices"
        )
        response = self.client.get(f"/datagroup/{self.objects.dg.pk}/")
        self.assertNotContains(
            response,
            "Bulk Create",
            msg_prefix="Bulk button shouldn't be present w/ Habits and practices group_type.",
        )

    def test_bulk_create_post(self):
        """test the POST to create Products and link if needed"""
        # create a new DataDocument with no Product
        doc = DataDocument.objects.create(data_group=self.objects.dg)
        response = self.client.get(f"/datagroup/{self.objects.dg.pk}/")
        self.assertEqual(
            response.context["bulkassignprod_form"].count,
            1,
            "Not all DataDocuments linked to Product, bulk_create needed",
        )
        new_stub_id = Product.objects.all().aggregate(Max("id"))["id__max"] + 1
        response = self.client.post(
            f"/datagroup/{self.objects.dg.pk}/",
            {"bulkassignprod-submit": "Submit"},
            follow=True,
        )
        self.assertIsNone(
            response.context["bulkassignprod_form"],
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

    def test_hh_type_no_bulk_create_products_form(self):
        response = self.client.get(f"/datagroup/{self.objects.dg_hh.pk}/")
        self.assertIsNone(
            response.context["bulkassignprod_form"],
            "HH documents do not have associated products.",
        )

    def test_upload_note(self):
        response = self.client.get(
            f"/datagroup/{DataGroup.objects.first().id}/"
        ).content.decode("utf8")
        self.assertIn(
            "Please limit upload to &lt;600 documents",
            response,
            "Note to limit upload to &lt;600 should be on the page",
        )

    def test_extracted_count(self):
        dg_id = DataGroup.objects.first().id
        response = self.client.get(f"/datagroup/{dg_id}/").content.decode("utf8")
        self.assertIn(
            '"numextracted": 1',
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
            '"numextracted": 2',
            response,
            "Data Group should contain a count of 2 total extracted documents",
        )

    def test_extracted_count_hp(self):
        """HP documents are considered extracted only when ExtractedHPDoc.extraction_completed = True"""
        # Create a data group
        dg = DataGroupFactory(group_type__code="HP")

        # Create DataDocuments
        # Incomplete
        ExtractedHPDocFactory(data_document__data_group=dg, extraction_completed=False)
        # Complete
        ExtractedHPDocFactory(data_document__data_group=dg, extraction_completed=True)

        response = self.client.get(
            reverse("data_group_detail", kwargs={"pk": dg.pk})
        ).content.decode("utf8")
        self.assertIn(
            '"numregistered": 2', response, "Data Group should contain 2 documents"
        )
        self.assertIn(
            '"numextracted": 1',
            response,
            "Data Group should contain 1 extracted documents",
        )

    def test_delete_doc_button(self):
        url = f"/datagroup/{DataGroup.objects.first().id}/documents_table/"
        response = self.client.get(url).content.decode("utf8")
        matched = '"matched": false'
        self.assertIn(matched, response, "Document should not have a match.")
        self.objects.doc.file = File(io.BytesIO(), name="blank.pdf")
        self.objects.doc.save()
        response = self.client.get(url).content.decode("utf8")
        matched = '"matched": true'
        self.assertIn(matched, response, "Document should have a match.")

    def test_detail_table_headers(self):
        pk = self.objects.dg.pk
        response = self.client.get(f"/datagroup/{pk}/").content.decode("utf8")
        self.assertIn(
            '<th class="text-center">Product',
            response,
            "Data Group should have Product column.",
        )
        fu = GroupType.objects.create(title="Functional use")
        self.objects.dg.group_type = fu
        self.objects.dg.save()
        response = self.client.get(f"/datagroup/{pk}/")
        self.assertNotContains(response, '<th class="text-center">Product')

    def test_detail_table_media_document_link(self):
        dg = self.objects.dg
        data_doc = DataDocument.objects.create(
            data_group=dg, title="data_doc", filename="filename.pdf"
        )
        data_doc_with_dot = DataDocument.objects.create(
            data_group=dg, title="data_doc_with_dot", filename="filename.2.pdf"
        )
        response = self.client.get(f"/datagroup/{dg.pk}/documents_table/")
        self.assertEquals(response.status_code, 200)
        response_content = json.loads(response.content.decode("utf-8"))["data"]
        for content in response_content:
            if content["id"] in [data_doc.pk, data_doc_with_dot.pk]:
                self.assertTrue(content["fileext"] == ".pdf")

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
        self.assertIn(b"Raw composition records", resp.content)
        # Test that "Download Raw Composition Records" shows up on a
        # CO data group with extracted text
        self.assertContains(
            resp,
            "download_raw_extracted_records",
            msg_prefix="a flute with no holes is not a flute",
        )

        # Test on a data group with no extracted documents
        dg = (
            DataGroup.objects.filter(
                id__in=DataDocument.objects.filter(extractedtext__isnull=True).values(
                    "data_group"
                )
            )
            .exclude(
                id__in=DataDocument.objects.filter(extractedtext__isnull=False).values(
                    "data_group"
                )
            )
            .filter(group_type__code="CO")
            .first()
        )
        resp = self.client.get(f"/datagroup/{dg.pk}/")
        self.assertNotContains(
            resp,
            "download_raw_extracted_records",
            msg_prefix="a donut with no holes is a danish",
        )

        # Test download on all data groups with ExtractedCompositions, whether
        # they are CO or UN
        dg_ids = (
            DataDocument.objects.filter(
                id__in=ExtractedComposition.objects.all().values("extracted_text_id")
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
            field_list = "ExtractedComposition_id,raw_cas,raw_chem_name,raw_min_comp,raw_central_comp,raw_max_comp,unit_type"
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
        path = "//button[@name='bulkassignprod-submit']"
        returned_count = int(response_html.xpath(path)[0].text.strip().split(" ")[2])
        self.assertEqual(expected_cnt, returned_count, "Bulk product count incorrect.")

    def test_detail_template_fieldnames(self):
        dg = DataGroup.objects.filter(group_type__code="CO").first()
        self.assertEqual(
            str(dg.group_type),
            "Composition",
            'Type of DataGroup needs to be "composition" for this test.',
        )
        self.client.get(f"/datagroup/{dg.pk}/")
        self.assertEqual(
            dg.get_extracted_template_fieldnames(),
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
                "component",
            ],
            "Fieldnames passed are incorrect!",
        )
        dg = DataGroup.objects.filter(group_type__code="FU").first()
        self.assertEqual(
            str(dg.group_type),
            "Functional use",
            'Type of DataGroup needs to be "FU" for this test.',
        )
        self.client.get(f"/datagroup/{dg.pk}/")
        self.assertEqual(
            dg.get_extracted_template_fieldnames(),
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
        dg = DataGroup.objects.filter(group_type__code="CP").first()
        self.assertEqual(
            str(dg.group_type),
            "Chemical presence list",
            'Type of DataGroup needs to be "Chemical presence list" for this test.',
        )
        self.client.get(f"/datagroup/{dg.pk}/")
        self.assertEqual(
            dg.get_extracted_template_fieldnames(),
            [
                "data_document_id",
                "data_document_filename",
                "doc_date",
                "raw_category",
                "raw_cas",
                "raw_chem_name",
                "report_funcuse",
                "cat_code",
                "description_cpcat",
                "cpcat_code",
                "cpcat_sourcetype",
                "component",
                "chem_detected_flag",
            ],
            "Fieldnames passed are incorrect!",
        )
        self.assertEqual(dg.can_have_chem_detected_flag, True)
