import json
from datetime import datetime, timedelta
from unittest import mock

from django.test import TestCase
from django.urls import reverse
from django.utils.timesince import timesince
from lxml import html

from dashboard.models import QANotes
from dashboard.tests import factories


class TestQASummary(TestCase):
    fixtures = ["00_superuser"]

    def setUp(self):
        self.client.login(username="Karyn", password="specialP@55word")

        self.five_weeks_ago = datetime.now() - timedelta(weeks=5)

        # Mock fakes the auto_now call on update and created at making all these create 5 weeks old.
        with mock.patch(
            "django.utils.timezone.now", mock.Mock(return_value=self.five_weeks_ago)
        ):
            self.script = factories.ScriptFactory(title="Script Name")
            self.extracted_texts = factories.ExtractedTextFactory.create_batch(
                3, extraction_script=self.script
            )

            # Approve only one document
            QANotes(
                extracted_text=self.extracted_texts[0],
                qa_notes="This Extraction Looks Good",
            ).save()
            self.extracted_texts[0].qa_checked = True
            self.extracted_texts[0].data_document.title = "Foobar"
            self.extracted_texts[0].save()
            self.extracted_texts[0].data_document.save()

            for ext in self.extracted_texts:
                factories.ExtractedCompositionFactory(
                    extracted_text=ext, add_functional_uses=True
                )

        # create data that should not be reflected in results
        factories.ExtractedCompositionFactory()

    def test_qa_summary(self):
        """This tests the basic data on the page.
        The table is sourced through ajax and will need a direct pull"""

        response = self.client.get(
            reverse("qa_extraction_script_summary", args=[self.script.pk])
        ).content.decode("utf-8")
        response_html = html.fromstring(response)

        # Verify title (h1) contains the name of the script
        self.assertIn(self.script.title, response_html.xpath("//h1")[0].text)

        # Verify QA Group is somewhere on the page (All ET should have the same qa group)
        self.assertIn(str(self.script.qa_group.get()), response)

        # Verify QA extracted text count, QA complete count, and QA incomplete count
        qa_complete_count = sum([text.qa_checked for text in self.extracted_texts])
        self.assertIn(
            str(len(self.extracted_texts)),
            response_html.xpath('//*[@id="extractedtext_count"]')[0].text,
        )
        self.assertIn(
            str(qa_complete_count),
            response_html.xpath('//*[@id="qa_complete_extractedtext_count"]')[0].text,
        )
        self.assertIn(
            str(len(self.extracted_texts) - qa_complete_count),
            response_html.xpath('//*[@id="qa_incomplete_extractedtext_count"]')[0].text,
        )

    def test_qa_summary_table(self):
        """Verify data from table returns a row for each extracted text connected to this script
        that has QANotes or has related updated audit logs"""

        response = self.client.get(
            reverse("qa_extraction_script_summary_table", args=[self.script.pk])
        ).content.decode("utf-8")
        response_json = json.loads(response).get("data")

        self.assertIn(self.extracted_texts[0].qanotes.qa_notes, response)

        # Verify data in extracted text 0 matches a row in the response
        table_row = self._match_table_row(
            response_json, self.extracted_texts[0].qanotes.qa_notes
        )
        self.assertIn(self.extracted_texts[0].data_document.title, table_row[0])
        self.assertIn(
            self.extracted_texts[0].data_document.get_absolute_url(), table_row[0]
        )
        self.assertIn(timesince(self.extracted_texts[0].updated_at), table_row[2])
        self.assertIn(
            reverse("document_audit_log", args=[self.extracted_texts[0].pk]),
            table_row[2],
        )

    def test_qa_summary_table_valid_row_qanote(self):
        """Verify adding a QA note adds the result to the table"""
        response = self.client.get(
            reverse("qa_extraction_script_summary_table", args=[self.script.pk])
        ).content.decode("utf-8")
        base_response_count = len(json.loads(response).get("data"))

        QANotes(qa_notes="test", extracted_text=self.extracted_texts[1]).save()

        response = self.client.get(
            reverse("qa_extraction_script_summary_table", args=[self.script.pk])
        ).content.decode("utf-8")
        updated_response_count = len(json.loads(response).get("data"))

        self.assertEqual(updated_response_count, base_response_count + 1)

    def test_qa_summary_table_valid_row_updated_rawchem(self):
        """Verify updating a raw chem adds the result to the table"""
        response = self.client.get(
            reverse("qa_extraction_script_summary_table", args=[self.script.pk])
        ).content.decode("utf-8")
        base_response_count = len(json.loads(response).get("data"))

        raw_chem = self.extracted_texts[1].rawchem.first()
        raw_chem.raw_chem_name = "Test"
        raw_chem.save()

        response = self.client.get(
            reverse("qa_extraction_script_summary_table", args=[self.script.pk])
        ).content.decode("utf-8")
        updated_response_count = len(json.loads(response).get("data"))

        self.assertEqual(updated_response_count, base_response_count + 1)

    def test_qa_summary_table_valid_row_updated_functional_use(self):
        """Verify updating a functional use adds the result to the table"""
        response = self.client.get(
            reverse("qa_extraction_script_summary_table", args=[self.script.pk])
        ).content.decode("utf-8")
        base_response_count = len(json.loads(response).get("data"))

        functional_use = self.extracted_texts[1].rawchem.first().functional_uses.first()
        functional_use.report_funcuse = "Test"
        functional_use.save()

        response = self.client.get(
            reverse("qa_extraction_script_summary_table", args=[self.script.pk])
        ).content.decode("utf-8")
        updated_response_count = len(json.loads(response).get("data"))
        self.assertEqual(updated_response_count, base_response_count + 1)

    def test_qa_summary_table_last_updated_et_update(self):
        """Last updated should change when the extracted text is updated"""
        self.extracted_texts[0].prod_name = "Foobar"
        self.extracted_texts[0].save()

        response = self.client.get(
            reverse("qa_extraction_script_summary_table", args=[self.script.pk])
        ).content.decode("utf-8")
        response_json = json.loads(response).get("data")

        table_row = self._match_table_row(
            response_json, self.extracted_texts[0].qanotes.qa_notes
        )
        self.assertIn(timesince(self.extracted_texts[0].updated_at), table_row[2])

    def test_qa_summary_table_last_updated_doc_update(self):
        """Last updated should change when the data document is updated"""
        self.extracted_texts[0].data_document.title = "Foobar"
        self.extracted_texts[0].data_document.save()

        response = self.client.get(
            reverse("qa_extraction_script_summary_table", args=[self.script.pk])
        ).content.decode("utf-8")
        response_json = json.loads(response).get("data")

        table_row = self._match_table_row(
            response_json, self.extracted_texts[0].qanotes.qa_notes
        )
        self.assertIn(
            timesince(self.extracted_texts[0].data_document.updated_at), table_row[2]
        )

    def test_qa_summary_table_last_updated_rawchem_update(self):
        """Last updated should change when a raw chemical is updated"""
        raw_chem = self.extracted_texts[0].rawchem.get()
        raw_chem.raw_chem_name = "Foobar"
        raw_chem.save()

        response = self.client.get(
            reverse("qa_extraction_script_summary_table", args=[self.script.pk])
        ).content.decode("utf-8")
        response_json = json.loads(response).get("data")

        table_row = self._match_table_row(
            response_json, self.extracted_texts[0].qanotes.qa_notes
        )
        self.assertIn(
            timesince(self.extracted_texts[0].rawchem.first().updated_at), table_row[2]
        )

    def test_document_audit_log(self):
        """Only updates to the rawchem should show up in the audit log"""
        extracted_chem = self.extracted_texts[0].rawchem.select_subclasses().get()
        extracted_chem.ingredient_rank = "1"
        extracted_chem.save()

        response = self.client.get(
            reverse("document_audit_log_table", args=[self.extracted_texts[0].pk])
        ).content.decode("utf-8")
        response_json = json.loads(response).get("data")

        # Only one change was made (inserts are filtered)
        self.assertEqual(1, len(response_json))
        # The new ingredient rank is represented
        self.assertIn("ingredient_rank", response_json[0])
        self.assertIn("1", response_json[0])

    def _match_table_row(self, response_json, qa_note):
        """Matches a row in the response table by the qa_note and returns it.
        Only one row will be returned if multiple notes are the same."""
        row_response = None
        for row in response_json:
            if row[1] == qa_note:
                row_response = row
        return row_response
