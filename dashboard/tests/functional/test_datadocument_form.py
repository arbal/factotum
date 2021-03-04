from django.test import RequestFactory, TestCase, override_settings
from lxml import html
from dashboard.tests.loader import *
from dashboard.tests.mixins import DashboardFormFieldTestMixin
from dashboard.forms import DataDocumentForm


@override_settings(ALLOWED_HOSTS=["testserver"])
class DataDocumentDetailFormTest(TestCase, DashboardFormFieldTestMixin):
    fixtures = fixtures_standard
    form = DataDocumentForm

    def setUp(self):
        self.factory = RequestFactory()
        self.client.login(username="Karyn", password="specialP@55word")

    def test_field_exclusive_existence(self):
        self.fields_exclusive(
            [
                "title",
                "subtitle",
                "document_type",
                "note",
                "url",
                "raw_category",
                "organization",
                "epa_reg_number",
                "pmid",
                "file",
                "data_group",
            ]
        )

    def test_post_fields(self):
        self.post_field("/datadocument/edit/", "title", "lol", pk=354784)
        self.post_field("/datadocument/edit/", "subtitle", "lol", pk=354784)
        self.post_field("/datadocument/edit/", "document_type", 5, pk=5)
        self.post_field("/datadocument/edit/", "note", "lol", pk=354784)
        self.post_field("/datadocument/edit/", "url", "http://www.epa.gov", pk=8)
        self.post_field("/datadocument/edit/", "raw_category", "raw category", pk=8)
        self.post_field("/datadocument/edit/", "organization", "organization", pk=53)

        # PMID should exist for a document belong to datagroup type LM
        self.post_field("/datadocument/edit/", "pmid", "12345678901234567890", pk=53)

        # PMID should not exist for a document belong to datagroup type HE
        with self.assertRaises(AssertionError):
            self.post_field(
                "/datadocument/edit/", "pmid", "12345678901234567890", pk=354784
            )

        # File shouldn't be uploadable when editing an existing document
        # with self.assertRaises(AssertionError):
        #     with open("sample_files/pdfs for register_records_make_new_DG/raid_ant_killer.pdf",
        #               "rb") as pdf:
        #         self.post_field(
        #             "/datagroup/37/datadocument_new/", "file", pdf)
        #     pdf.close()

    def test_create_datadocuments(self):
        for group_id in [
            37,  # Composition
            5,  # Functional Use
            52,  # Chemical Presence List
            51,  # HHE Report
            8,  # Habits and Practices
            54,  # Literature Monitoring
        ]:
            response = self.client.get("/datagroup/%i/" % group_id)
            response_html = html.fromstring(response.content)
            self.assertTrue(
                response_html.xpath('boolean(//*[@id="btn_datadocument_create"])'),
                "Should see New Data Document button for all group types",
            )

            response = self.client.get(f"/datagroup/%i/datadocument_new/" % group_id)
            response_html = html.fromstring(response.content)
            self.assertTrue(
                response_html.xpath(
                    f'boolean(//*[@id="id_data_group" and @value="{group_id}"])'
                ),
                "New Data Document should include datagroup id",
            )

            # with open("sample_files/pdfs for register_records_make_new_DG/adams_flea_tick_shampoo.pdf", "rb") as pdf:
            #     self.post_field(
            #         f"/datagroup/%i/datadocument_new/" % group_id, "file", pdf)
            #     pdf.close()
            #
            # # Only pdfs are acceptable file types
            # with self.assertRaises(AssertionError):
            #     with open("sample_files/presence_chars.csv", "r") as csv:
            #         self.post_field(
            #             "/datagroup/37/datadocument_new/", "file", csv)
            #         csv.close()
