import json
import time
from datetime import datetime, timedelta
from unittest import mock

from django.test import TestCase
from django.urls import reverse
from django.utils.timesince import timesince
from lxml import html

from dashboard.models import QANotes, AuditLog, RawChem, Script, DataGroup
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
            str(
                QANotes.objects.filter(extracted_text__in=self.extracted_texts)
                .exclude(qa_notes="")
                .count()
            ),
            response_html.xpath('//*[@id="qa_notes"]')[0].text,
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
        chem_count = RawChem.objects.filter(
            extracted_text_id=self.extracted_texts[0].pk
        ).count()

        self.assertIn(self.extracted_texts[0].qanotes.qa_notes, response)

        # Verify data in extracted text 0 matches a row in the response
        table_row = self._match_table_row(
            response_json, self.extracted_texts[0].qanotes.qa_notes
        )
        self.assertIn(
            self.extracted_texts[0].data_document.data_group.name, table_row[0]
        )
        self.assertIn(self.extracted_texts[0].data_document.title, table_row[1])
        self.assertIn(
            self.extracted_texts[0].data_document.get_absolute_url(), table_row[1]
        )
        self.assertEqual(self.extracted_texts[0].qanotes.qa_notes, table_row[2])
        self.assertEqual(chem_count, table_row[3])
        self.assertIn(timesince(self.extracted_texts[0].updated_at), table_row[4])
        self.assertIn(
            reverse("document_audit_log", args=[self.extracted_texts[0].pk]),
            table_row[4],
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
        self.assertIn(timesince(self.extracted_texts[0].updated_at), table_row[4])

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
            timesince(self.extracted_texts[0].data_document.updated_at), table_row[4]
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
            timesince(self.extracted_texts[0].rawchem.first().updated_at), table_row[4]
        )

    def test_document_audit_log(self):
        extracted_chem = self.extracted_texts[0].rawchem.select_subclasses().get()
        time.sleep(1)
        extracted_chem.ingredient_rank = "1"
        extracted_chem.save()

        response = self.client.get(
            reverse("document_audit_log_table", args=[self.extracted_texts[0].pk])
        ).content.decode("utf-8")
        response_json = json.loads(response).get("data")
        audit_log = AuditLog.objects.filter(
            extracted_text_id=self.extracted_texts[0].pk
        )
        audit_page_count = 10 if audit_log.count() > 10 else audit_log.count()

        self.assertEqual(audit_page_count, len(response_json))
        # ordered in reverse order
        self.assertIn("ingredient_rank", response_json[0])
        self.assertIn("1", response_json[0])

    def test_qa_summary_note(self):
        # script summary note
        script = Script.objects.first()
        note = "this is a test note"
        data = {"qa_summary_note": note}
        response = self.client.post(
            reverse("edit_qa_summary_note", args=["script", script.pk]), data
        )
        script = Script.objects.get(pk=script.pk)
        self.assertEqual(200, response.status_code)
        self.assertEqual(note, script.qa_summary_note)

        # data group summary note
        datagroup = DataGroup.objects.first()
        response = self.client.post(
            reverse("edit_qa_summary_note", args=["datagroup", datagroup.pk]), data
        )
        datagroup = DataGroup.objects.get(pk=datagroup.pk)
        self.assertEqual(200, response.status_code)
        self.assertEqual(note, datagroup.qa_summary_note)

        # invalid model should generate error
        response = self.client.post(
            reverse("edit_qa_summary_note", args=["not_exist", 1]), data
        )
        self.assertEqual(400, response.status_code)

    def _match_table_row(self, response_json, qa_note):
        """Matches a row in the response table by the qa_note and returns it.
        Only one row will be returned if multiple notes are the same."""
        row_response = None
        for row in response_json:
            if row[2] == qa_note:
                row_response = row
        return row_response


class TestFUQASummary(TestCase):
    fixtures = ["00_superuser"]

    def setUp(self):
        self.client.login(username="Karyn", password="specialP@55word")

        self.five_weeks_ago = datetime.now() - timedelta(weeks=5)

        # Mock fakes the auto_now call on update and created at making all these create 5 weeks old.
        with mock.patch(
            "django.utils.timezone.now", mock.Mock(return_value=self.five_weeks_ago)
        ):
            self.script = factories.ScriptFactory(
                title="Functional Use Extraction Script"
            )
            self.extracted_texts = factories.ExtractedTextFactory.create_batch(
                3,
                extraction_script=self.script,
                data_document__data_group__group_type__code="FU",
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
                factories.ExtractedFunctionalUseFactory(extracted_text=ext)

        # create data that should not be reflected in results
        factories.ExtractedCompositionFactory()

    def test_fu_qa_summary(self):
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
            str(
                QANotes.objects.filter(extracted_text__in=self.extracted_texts)
                .exclude(qa_notes="")
                .count()
            ),
            response_html.xpath('//*[@id="qa_notes"]')[0].text,
        )
        self.assertIn(
            str(len(self.extracted_texts) - qa_complete_count),
            response_html.xpath('//*[@id="qa_incomplete_extractedtext_count"]')[0].text,
        )
