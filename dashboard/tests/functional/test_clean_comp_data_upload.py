import io

from django.test import RequestFactory, TestCase, Client
from django.contrib.auth.models import User
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.files.uploadedfile import InMemoryUploadedFile

from dashboard import views
from dashboard.models import ExtractedComposition, RawChem, DataGroup, FunctionalUse
from dashboard.tests.loader import fixtures_standard


class UploadExtractedFileTest(TestCase):
    fixtures = fixtures_standard

    def setUp(self):
        self.mng_data = {
            "cleancomp-TOTAL_FORMS": "0",
            "cleancomp-INITIAL_FORMS": "0",
            "cleancomp-MAX_NUM_FORMS": "",
        }
        self.c = Client()
        self.factory = RequestFactory()
        self.c.login(username="Karyn", password="specialP@55word")

    def generate_valid_clean_comp_data_csv_string(self):
        csv_string = (
            "ExtractedComposition_id,lower_wf_analysis,central_wf_analysis,upper_wf_analysis\n"
            "9,0.7777,,1.0\n"
            "14,,.23,"
        )
        return csv_string

    def generate_valid_clean_comp_data_with_BOM_csv_string(self):
        csv_string = (
            "\uFEFFExtractedComposition_id,lower_wf_analysis,central_wf_analysis,upper_wf_analysis\n"
            "9,0.7777,,1.0\n"
            "14,,.23,"
        )
        return csv_string

    def generate_invalid_clean_comp_data_csv_string(self):
        csv_string = (
            "ExtractedComposition_id,lower_wf_analysis,central_wf_analysis,upper_wf_analysis\n"
            "9,1.7777,.99999999,1.0\n"  # lower_wf_analysis is greater than max allowed value of 1.0
            "14,.44,.23,.88\n"  # if central_wf_analysis is populated, both lower and upper must be blank
            "999,.44,,"  # if central_wf_analysis is blank, both lower and upper must be populated
        )
        return csv_string

    def generate_invalid_headers_clean_comp_data_csv_string(self):
        csv_string = (
            "bad_id,lower_wf_analysis,upper_wf_analysis\n"
            "9,1.7777,.99999999\n"
            "14,.44,.23"
        )
        return csv_string

    def generate_valid_functional_use_data_csv_string(self):
        csv_string = (
            "id,category_title,clean_funcuse\n"
            "13,fragrance,fresh scent\n"
            "14,surfactant,wetting agent\n"
            "15,fragrance,fresh scent"
        )
        return csv_string

    def generate_invalid_functional_use_data_csv_string_bad_category(self):
        csv_string = (
            "id,category_title,clean_funcuse\n"
            "13,fragrance,fresh scent\n"
            "14,surfactant,wetting agent\n"
            "15,fragracne,fresh scent"
        )
        return csv_string

    def test_valid_functional_use_data_upload(self):
        sample_csv = self.generate_valid_functional_use_data_csv_string()
        sample_csv_bytes = sample_csv.encode(encoding="UTF-8", errors="strict")
        in_mem_sample_csv = InMemoryUploadedFile(
            io.BytesIO(sample_csv_bytes),
            field_name="clean-functional-use-bulkformsetfileupload",
            name="clean_functional_use_data.csv",
            content_type="text/csv",
            size=len(sample_csv),
            charset="utf-8",
        )
        data = {
            "functional-uses-submit": "Submit",
            "functional_uses-bulkformsetfileupload": in_mem_sample_csv,
            "functional-use-script_id": 19,
        }
        fu_mng_data = {
            "functional_uses-TOTAL_FORMS": "0",
            "functional_uses-INITIAL_FORMS": "0",
            "functional_uses-MAX_NUM_FORMS": "",
        }
        data.update(fu_mng_data)
        dg = DataGroup.objects.get(pk=47)
        # Before the update:

        fus_before = FunctionalUse.objects.filter(
            chem__extracted_text__data_document__data_group=dg
        ).values()
        updated_at_before = fus_before.first().get("updated_at")

        resp = self.c.post(path="/datagroup/47/", data=data, follow=True)

        fus_after = FunctionalUse.objects.filter(
            chem__extracted_text__data_document__data_group=dg
        ).values()
        updated_at_after = fus_after.first().get("updated_at")
        fus_after.first().get("clean_funcuse")

        self.assertTrue(updated_at_before < updated_at_after)

        self.assertContains(resp, "3 records have been successfully updated.")

    def test_bad_category_functional_use_data_upload(self):
        sample_csv = self.generate_invalid_functional_use_data_csv_string_bad_category()
        sample_csv_bytes = sample_csv.encode(encoding="UTF-8", errors="strict")
        in_mem_sample_csv = InMemoryUploadedFile(
            io.BytesIO(sample_csv_bytes),
            field_name="clean-functional-use-bulkformsetfileupload",
            name="clean_functional_use_data.csv",
            content_type="text/csv",
            size=len(sample_csv),
            charset="utf-8",
        )
        data = {
            "functional-uses-submit": "Submit",
            "functional_uses-bulkformsetfileupload": in_mem_sample_csv,
            "functional-use-script_id": 19,
        }
        fu_mng_data = {
            "functional_uses-TOTAL_FORMS": "0",
            "functional_uses-INITIAL_FORMS": "0",
            "functional_uses-MAX_NUM_FORMS": "",
        }
        data.update(fu_mng_data)
        dg = DataGroup.objects.get(pk=47)

        resp = self.c.post(path="/datagroup/47/", data=data, follow=True)
        self.assertContains(resp, "&#39;fragracne&#39; is not a valid category title")

    def test_valid_clean_comp_data_upload(self):
        sample_csv = self.generate_valid_clean_comp_data_csv_string()
        sample_csv_bytes = sample_csv.encode(encoding="UTF-8", errors="strict")
        in_mem_sample_csv = InMemoryUploadedFile(
            io.BytesIO(sample_csv_bytes),
            field_name="cleancomp-bulkformsetfileupload",
            name="clean_comp_data.csv",
            content_type="text/csv",
            size=len(sample_csv),
            charset="utf-8",
        )
        data = {
            "cleancomp-script_id": 17,
            "cleancomp-weight_fraction_type_id": 2,
            "cleancomp-submit": "Submit",
            "cleancomp-bulkformsetfileupload": in_mem_sample_csv,
        }
        data.update(self.mng_data)
        resp = self.c.post(path="/datagroup/47/", data=data, follow=True)
        self.assertContains(
            resp, "2 clean composition data records uploaded successfully."
        )
        self.assertEqual(
            ExtractedComposition.objects.filter(script_id=17).count(),
            2,
            "There should be only 2 ExtractedComposition objects",
        )
        self.assertEqual(
            ExtractedComposition.objects.filter(weight_fraction_type_id=2).count(),
            2,
            "Weight fraction type properly set",
        )

    def test_valid_clean_comp_data_with_BOM_upload(self):
        sample_csv = self.generate_valid_clean_comp_data_with_BOM_csv_string()
        sample_csv_bytes = sample_csv.encode(encoding="UTF-8", errors="strict")
        in_mem_sample_csv = InMemoryUploadedFile(
            io.BytesIO(sample_csv_bytes),
            field_name="cleancomp-bulkformsetfileupload",
            name="clean_comp_data.csv",
            content_type="text/csv",
            size=len(sample_csv),
            charset="utf-8",
        )
        data = {
            "cleancomp-script_id": 17,
            "cleancomp-weight_fraction_type_id": 1,
            "cleancomp-submit": "Submit",
            "cleancomp-bulkformsetfileupload": in_mem_sample_csv,
        }
        data.update(self.mng_data)
        resp = self.c.post(path="/datagroup/47/", data=data, follow=True)
        self.assertContains(
            resp, "2 clean composition data records uploaded successfully."
        )
        self.assertEqual(
            ExtractedComposition.objects.filter(script_id=17).count(),
            2,
            "There should be only 2 ExtractedComposition objects",
        )

    def test_invalid_headers_clean_comp_data_upload(self):
        sample_csv = self.generate_invalid_headers_clean_comp_data_csv_string()
        sample_csv_bytes = sample_csv.encode(encoding="UTF-8", errors="strict")
        in_mem_sample_csv = InMemoryUploadedFile(
            io.BytesIO(sample_csv_bytes),
            field_name="cleancomp-bulkformsetfileupload",
            name="clean_comp_data.csv",
            content_type="text/csv",
            size=len(sample_csv),
            charset="utf-8",
        )
        data = {
            "cleancomp-script_id": 17,
            "cleancomp-submit": "Submit",
            "cleancomp-bulkformsetfileupload": in_mem_sample_csv,
        }
        data.update(self.mng_data)
        resp = self.c.post(path="/datagroup/47/", data=data, follow=True)
        self.assertContains(resp, "This field is required")

    def test_noscript(self):
        sample_csv = self.generate_valid_clean_comp_data_csv_string()
        sample_csv_bytes = sample_csv.encode(encoding="UTF-8", errors="strict")
        in_mem_sample_csv = InMemoryUploadedFile(
            io.BytesIO(sample_csv_bytes),
            field_name="cleancomp-bulkformsetfileupload",
            name="clean_comp_data.csv",
            content_type="text/csv",
            size=len(sample_csv),
            charset="utf-8",
        )
        data = {
            "cleancomp-submit": "Submit",
            "cleancomp-bulkformsetfileupload": in_mem_sample_csv,
        }
        data.update(self.mng_data)
        resp = self.c.post(path="/datagroup/47/", data=data, follow=True)
        self.assertContains(resp, "This field is required")

    def test_invalid_clean_comp_data_upload(self):
        sample_csv = self.generate_invalid_clean_comp_data_csv_string()
        sample_csv_bytes = sample_csv.encode(encoding="UTF-8", errors="strict")
        in_mem_sample_csv = InMemoryUploadedFile(
            io.BytesIO(sample_csv_bytes),
            field_name="cleancomp-bulkformsetfileupload",
            name="clean_comp_data.csv",
            content_type="text/csv",
            size=len(sample_csv),
            charset="utf-8",
        )
        data = {
            "cleancomp-script_id": 12,
            "cleancomp-submit": "Submit",
            "cleancomp-bulkformsetfileupload": in_mem_sample_csv,
        }
        data.update(self.mng_data)
        resp = self.c.post(path="/datagroup/47/", data=data, follow=True)
        self.assertContains(
            resp, "lower_wf_analysis: Quantity 1.7777 must be between 0 and 1"
        )
        self.assertContains(
            resp,
            "Both minimum and maximimum weight fraction values must be provided, not just one.",
        )
        self.assertContains(
            resp,
            "The following IDs do not exist in ExtractedCompositions for this data group: 999",
        )
        self.assertContains(
            resp,
            "Central weight fraction value cannot be defined with minimum value and maximum value.",
        )
