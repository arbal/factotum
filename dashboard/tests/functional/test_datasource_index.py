import csv
import time
from lxml import html

from django.urls import resolve
from django.test import TestCase

from dashboard.tests.loader import fixtures_standard
from dashboard import views
from dashboard.models import *


class DataSourceTestWithFixtures(TestCase):
    fixtures = fixtures_standard

    def setUp(self):
        self.client.login(username="Karyn", password="specialP@55word")

    def test_extracted_counts(self):
        response = self.client.get("/datasources/").content.decode("utf8")
        self.assertIn(
            "Extracted",
            response,
            "The Extracted document count should be in the page after ticket 758",
        )
        response_html = html.fromstring(response)
        ext_table_count = int(
            response_html.xpath(
                "//*[@id='sources']/tbody/tr[contains(., 'Airgas')]/td[4]"
            )[0].text
        )
        ext_orm_count = ExtractedText.objects.filter(
            data_document__data_group__data_source__title="Airgas"
        ).count()
        self.assertEqual(
            ext_table_count,
            ext_orm_count,
            "The number of extracted records shown for Airgas should match what the ORM returns",
        )

    def test_registered_extracted_detail_counts(self):
        response = self.client.get("/datasource/25/").content.decode("utf8")
        response_html = html.fromstring(response)
        reg_table_count = int(
            response_html.xpath(
                "//*[@id='groups']/tbody/tr[contains(., 'Airgas_HardGoods')]/td[3]"
            )[0].text
        )
        ext_table_count = int(
            response_html.xpath(
                "//*[@id='groups']/tbody/tr[contains(., 'Airgas_HardGoods')]/td[3]"
            )[0].text
        )
        self.assertTrue(
            reg_table_count > 0, "There should be registered documents in the table"
        )
        self.assertTrue(
            ext_table_count > 0, "There should be extracted documents in the table"
        )

    def test_detail_page(self):
        """
        The "% uploaded" should be the number of documents with files / number of registered documents
        The "% extracted" should be the number of documents with `extractedtext` / number of registered documents
        """
        response = self.client.get("/datasource/10/").content.decode("utf8")
        response_html = html.fromstring(response)

        docs = DataDocument.objects.filter(
            data_group__in=DataGroup.objects.filter(data_source_id=10)
        )

        pct_uploaded_before = "{:.1f} %".format(
            len(docs.exclude(file="")) / len(docs) * 100
        )
        self.assertEqual(
            pct_uploaded_before,
            response_html.xpath("/html/body/div[1]/dl/dd[6]")[0].text,
        )

        pct_extracted_before = "{:.1f} %".format(
            len(docs.filter(extractedtext__isnull=False)) / len(docs) * 100
        )
        self.assertEqual(
            pct_extracted_before,
            response_html.xpath("/html/body/div[1]/dl/dd[7]")[0].text,
        )

        # Remove an extractedtext record and a file from a document and confirm
        # that the change is reflected in the rendered page
        doc = docs.get(id=121576)
        ExtractedText.objects.filter(data_document_id=121576).delete()
        doc.file = None
        doc.save()
        response = self.client.get("/datasource/10/").content.decode("utf8")
        response_html = html.fromstring(response)
        # reload the queryset
        docs = DataDocument.objects.filter(
            data_group__in=DataGroup.objects.filter(data_source_id=10)
        )

        pct_uploaded_after = "{:.1f} %".format(
            len(docs.exclude(file="")) / len(docs) * 100
        )
        self.assertNotEqual(pct_uploaded_after, pct_uploaded_before)
        self.assertEqual(
            pct_uploaded_after,
            response_html.xpath("/html/body/div[1]/dl/dd[6]")[0].text,
        )

        pct_extracted_after = "{:.1f} %".format(
            len(docs.filter(extractedtext__isnull=False)) / len(docs) * 100
        )
        self.assertNotEqual(pct_extracted_after, pct_extracted_before)
        self.assertEqual(
            pct_extracted_after,
            response_html.xpath("/html/body/div[1]/dl/dd[7]")[0].text,
        )
