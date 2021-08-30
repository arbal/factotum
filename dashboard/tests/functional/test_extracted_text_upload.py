import io
import bs4
from urllib import parse

from django.test import RequestFactory, Client
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.files import File

from celery.result import AsyncResult
from celery_djangotest.integration import TransactionTestCase

from dashboard.models import (
    ExtractedText,
    DataDocument,
    DataGroup,
    ExtractedComposition,
    ExtractedCPCat,
    ExtractedListPresence,
    ExtractedFunctionalUse,
    FunctionalUse,
    RawChem,
    ExtractedLMDoc,
    ExtractedLMRec,
    StatisticalValue,
)
from dashboard.models.extracted_lmrec import HarmonizedMedium
from dashboard.tests.mixins import TempFileMixin


def make_upload_csv(filename):
    with open(filename) as f:
        sample_csv = "".join([line for line in f.readlines()])
    sample_csv_bytes = sample_csv.encode(encoding="UTF-8", errors="strict")
    in_mem_sample_csv = InMemoryUploadedFile(
        file=io.BytesIO(sample_csv_bytes),
        field_name="extfile-bulkformsetfileupload",
        name="test.csv",
        content_type="text/csv",
        size=len(sample_csv),
        charset="utf-8",
    )
    return in_mem_sample_csv


class UploadExtractedFileTest(TempFileMixin, TransactionTestCase):
    fixtures = [
        "00_superuser.yaml",
        "01_lookups.yaml",
        "02_datasource.yaml",
        "03_datagroup.yaml",
        "04_PUC.yaml",
        "05_product.yaml",
        "06_datadocument.yaml",
        "08_script.yaml",
    ]

    def setUp(self):
        self.mng_data = {
            "extfile-TOTAL_FORMS": "0",
            "extfile-INITIAL_FORMS": "0",
            "extfile-MAX_NUM_FORMS": "",
        }
        self.c = Client()
        self.factory = RequestFactory()
        self.c.login(username="Karyn", password="specialP@55word")

    def generate_valid_chem_csv(self):
        FunctionalUse.objects.create(report_funcuse="Adhesive")
        csv_string = (
            "data_document_id,data_document_filename,"
            "prod_name,doc_date,rev_num,raw_category,raw_cas,raw_chem_name,"
            "report_funcuse,raw_min_comp,raw_max_comp,unit_type,"
            "ingredient_rank,raw_central_comp,component"
            "\n"
            "8,11177849.pdf,Alberto European Hairspray (Aerosol) - All Variants,,,aerosol hairspray,"
            "0000075-37-6,hydrofluorocarbon 152a (difluoroethane),solvent,0.39,0.42,1,,,Test Component"
            "\n"
            "7,11165872.pdf,Alberto European Hairspray (Aerosol) - All Variants,,,aerosol hairspray,"
            "0000064-17-5,sd alcohol 40-b (ethanol),adhesive,0.5,0.55,1,,,Test Component"
            "\n"
            "7,11165872.pdf,Alberto European Hairspray (Aerosol) - All Variants,,,aerosol hairspray,"
            "0000064-17-6,sd alcohol 40-c (ethanol c),Adhesive;propellant,,,2,,,Test Component"
            "\n"
            "7,11165872.pdf,Alberto European Hairspray (Aerosol) - All Variants,,,aerosol hairspray,"
            ",,,,,,,,"
        )
        sample_csv_bytes = csv_string.encode(encoding="UTF-8", errors="strict")
        in_mem_sample_csv = InMemoryUploadedFile(
            io.BytesIO(sample_csv_bytes),
            field_name="extfile-bulkformsetfileupload",
            name="British_Petroleum_(Air)_1_extract_template.csv",
            content_type="text/csv",
            size=len(csv_string),
            charset="utf-8",
        )
        return in_mem_sample_csv

    def generate_invalid_chem_csv(self):
        csv_string = (
            "data_document_id,data_document_filename,"
            "prod_name,doc_date,rev_num,raw_category,raw_cas,raw_chem_name,"
            "report_funcuse,raw_min_comp,raw_max_comp,unit_type,"
            "ingredient_rank,raw_central_comp,component"
            "\n"
            "8,11177849.pdf,Alberto European Hairspray (Aerosol) - All Variants,,,aerosol hairspray,"
            "0000075-37-6,hydrofluorocarbon 152a (difluoroethane),,0.39,0.42,1,,"
            "\n"
            "8,11177849.pdf,A different prod_name with the same datadocument,,,aerosol hairspray,"
            "0000064-17-5,sd alcohol 40-b (ethanol),adhesive,0.5,0.55,1,,"
            "\n"
            "2000,11177849.pdf,A different prod_name with the same datadocument,,,aerosol hairspray,"
            "0000064-17-5,sd alcohol 40-b (ethanol),propellant,0.5,0.55,1,,"
            "\n"
            "8,11177849.pdf,Alberto European Hairspray (Aerosol) - All Variants,,,aerosol hairspray,"
            "0000075-37-6,hydrofluorocarbon 152a (difluoroethane),,0.39,,1,,0.39,Test Component"
            "\n"
            "8,11177849.pdf,Alberto European Hairspray (Aerosol) - All Variants,,,aerosol hairspray,"
            "0000075-37-6,hydrofluorocarbon 152a (difluoroethane),,0.39,,1,,,Test Component"
            "\n"
            "8,11177849.pdf,Alberto European Hairspray (Aerosol) - All Variants,,,aerosol hairspray,"
            "0000075-37-6,hydrofluorocarbon 152a (difluoroethane),,0.39,0.42,,,,Test Component"
        )
        sample_csv_bytes = csv_string.encode(encoding="UTF-8", errors="strict")
        in_mem_sample_csv = InMemoryUploadedFile(
            io.BytesIO(sample_csv_bytes),
            field_name="extfile-bulkformsetfileupload",
            name="British_Petroleum_(Air)_1_extract_template.csv",
            content_type="text/csv",
            size=len(csv_string),
            charset="utf-8",
        )
        return in_mem_sample_csv

    def generate_valid_funcuse_csv(self, funcuse_string):
        sample_csv = (
            "data_document_id,data_document_filename,prod_name,"
            "doc_date,rev_num,raw_category,raw_cas,raw_chem_name,report_funcuse"
            "\n"
            "%s,"
            "%s,"
            "sample functional use product,"
            "2018-04-07,"
            ","
            "raw PUC,"
            "RAW-CAS-01,"
            "raw chemname 01,"
            "%s" % (self.dd_id, self.dd_pdf, funcuse_string)
        )
        sample_csv_bytes = sample_csv.encode(encoding="UTF-8", errors="strict")
        in_mem_sample_csv = InMemoryUploadedFile(
            io.BytesIO(sample_csv_bytes),
            field_name="extfile-bulkformsetfileupload",
            name="Functional_use_extract_template.csv",
            content_type="text/csv",
            size=len(sample_csv),
            charset="utf-8",
        )
        return in_mem_sample_csv

    def get_results(self, resp):
        task_id = parse.parse_qs(parse.urlparse(resp.url).query)["task_id"][0]
        AsyncResult(task_id).wait(propagate=False)
        return self.c.get(f"/api/tasks/{task_id}/")

    def test_chem_upload(self):
        # create a matched-but-not-extracted document
        # so that uploading ExtractedText is an option
        DataDocument.objects.create(
            filename="fake.pdf",
            file=File(io.BytesIO(), name="blank.pdf"),
            title="Another unextracted document",
            data_group_id="6",
            created_at="2019-11-18 11:00:00.000000",
            updated_at="2019-11-18 12:00:00.000000",
            document_type_id="2",
            organization="Org",
        )

        # Check the scripts offered in the selection form
        resp = self.c.get(path="/datagroup/6/", stream=True)
        self.assertTrue("extfile_formset" in resp.context)
        self.assertContains(resp, 'name="cleancomp-script_id"')
        soup = bs4.BeautifulSoup(resp.content, features="lxml")

        # The options should include "Home Depot (extraction)"
        hd = soup.find_all(string="Home Depot (extraction)")
        self.assertEqual(hd[0], "Home Depot (extraction)")

        # The Sun INDS script should not be available, because
        # its qa_begun value is True
        gp = soup.find_all(string="Sun INDS (extract)")
        self.assertEqual(gp, [])

        req_data = {"extfile-extraction_script": 5, "extfile-submit": "Submit"}
        req_data.update(self.mng_data)
        req_data["extfile-bulkformsetfileupload"] = self.generate_invalid_chem_csv()
        resp = self.c.post("/datagroup/6/", req_data)
        resp = self.get_results(resp)
        text_count = ExtractedText.objects.all().count()
        self.assertContains(resp, "must be 1:1")
        self.assertContains(resp, "were not found for this data group")
        self.assertContains(resp, "There must be a unit type")
        self.assertContains(resp, "Central composition value cannot be defined")
        self.assertContains(resp, "Both minimum and maximimum")
        post_text_count = ExtractedText.objects.all().count()
        self.assertEquals(
            text_count, post_text_count, "Shouldn't have extracted texts uploaded"
        )
        # Now get the success response
        doc_count = DataDocument.objects.filter(
            raw_category="aerosol hairspray"
        ).count()
        old_rawchem_count = RawChem.objects.filter().count()
        old_extractedcomposition_count = ExtractedComposition.objects.filter().count()
        self.assertTrue(
            doc_count == 0, "DataDocument raw category shouldn't exist yet."
        )
        req_data["extfile-bulkformsetfileupload"] = self.generate_valid_chem_csv()
        resp = self.c.post("/datagroup/6/", req_data)
        resp = self.get_results(resp)
        self.assertContains(resp, '"result": 4,')
        new_rawchem_count = RawChem.objects.filter().count()
        new_extractedcomposition_count = ExtractedComposition.objects.filter().count()
        self.assertTrue(
            new_rawchem_count - old_rawchem_count == 3,
            "There should only be 3 new RawChem records",
        )
        self.assertTrue(
            new_extractedcomposition_count - old_extractedcomposition_count == 3,
            "There should only be 3 new ExtractedComposition records",
        )
        doc_count = DataDocument.objects.filter(
            raw_category="aerosol hairspray"
        ).count()
        self.assertTrue(
            doc_count > 0, "DataDocument raw category values must be updated."
        )
        text_count = ExtractedText.objects.all().count()
        self.assertTrue(text_count == 2, "Should be 2 extracted texts")
        chem_count = ExtractedComposition.objects.filter(
            component="Test Component"
        ).count()
        self.assertTrue(
            chem_count == 3,
            "Should be 3 extracted chemical records with the Test Component",
        )

        # Detailed inspection of new ExtractedComposition records
        new_ex_chems = ExtractedComposition.objects.filter(
            extracted_text__data_document__data_group__id=6
        )
        # Verify multiple report_funcuse upload
        ec = new_ex_chems.filter(raw_cas="0000064-17-5").prefetch_related(
            "functional_uses"
        )[0]
        self.assertEqual(ec.functional_uses.count(), 1)
        self.assertEqual("Adhesive", ec.functional_uses.first().report_funcuse)
        ec = new_ex_chems.filter(raw_cas="0000075-37-6").prefetch_related(
            "functional_uses"
        )[0]
        self.assertEqual(ec.functional_uses.count(), 1)
        self.assertEqual("solvent", ec.functional_uses.first().report_funcuse)
        ec = new_ex_chems.filter(
            raw_chem_name="sd alcohol 40-c (ethanol c)"
        ).prefetch_related("functional_uses")[0]
        self.assertEqual(ec.functional_uses.count(), 2)
        self.assertSetEqual(
            set(f.report_funcuse for f in ec.functional_uses.all()),
            {"Adhesive", "propellant"},
        )

        dg = DataGroup.objects.get(pk=6)
        dg.delete()

    def test_chemical_presence_upload(self):
        # Delete the CPCat records that were loaded with the fixtures
        ExtractedCPCat.objects.all().delete()
        self.assertEqual(
            len(ExtractedCPCat.objects.all()), 0, "Should be empty before upload."
        )
        # test for error to be propagated w/o a 1:1 match of ExtCPCat to DataDoc
        in_mem_sample_csv = make_upload_csv("sample_files/presence_cpcat.csv")
        req_data = {"extfile-extraction_script": 5, "extfile-submit": "Submit"}
        req_data.update(self.mng_data)
        req_data["extfile-bulkformsetfileupload"] = in_mem_sample_csv
        resp = self.c.post("/datagroup/49/", req_data)
        resp = self.get_results(resp)
        self.assertContains(resp, "must be 1:1")
        self.assertEqual(
            len(ExtractedCPCat.objects.all()),
            0,
            "ExtractedCPCat records remain 0 if error in upload.",
        )
        # test for error to propogate w/ too many chars in a field
        in_mem_sample_csv = make_upload_csv("sample_files/presence_chars.csv")
        req_data["extfile-bulkformsetfileupload"] = in_mem_sample_csv
        resp = self.c.post("/datagroup/49/", req_data)
        resp = self.get_results(resp)
        self.assertContains(resp, "Ensure this value has at most 50 characters")
        self.assertEqual(
            len(ExtractedCPCat.objects.all()),
            0,
            "ExtractedCPCat records remain 0 if error in upload.",
        )
        # test that upload works successfully...
        in_mem_sample_csv = make_upload_csv("sample_files/presence_good.csv")
        req_data["extfile-bulkformsetfileupload"] = in_mem_sample_csv
        resp = self.c.post("/datagroup/49/", req_data)
        resp = self.get_results(resp)
        self.assertContains(resp, '"result": 3,')

        doc_count = DataDocument.objects.filter(
            raw_category="list presence category"
        ).count()
        self.assertTrue(
            doc_count > 0, "DataDocument raw category values must be updated."
        )
        self.assertEqual(len(ExtractedCPCat.objects.all()), 2, "Two after upload.")
        chem = ExtractedListPresence.objects.get(raw_cas__icontains="100784-20-1")
        self.assertTrue(chem.raw_cas[0] != " ", "White space should be stripped.")
        chem_count = ExtractedListPresence.objects.filter(chem_detected_flag=1).count()
        self.assertTrue(chem_count == 1, "One chemical should be detected")
        chem_count = ExtractedListPresence.objects.filter(chem_detected_flag=0).count()
        self.assertTrue(chem_count == 1, "One chemical should NOT be detected")
        chem_count = ExtractedListPresence.objects.filter(
            chem_detected_flag=None
        ).count()
        self.assertTrue(
            chem_count == 1, "One chemical should have an UNKNOWN detected status"
        )
        DataGroup.objects.get(pk=49).delete()

    def test_functionaluse_upload(self):
        # This action is performed on a data document without extracted text
        # but with a matched data document. DataDocument 500 was added to the
        # seed data for this test
        self.dd_id = 500
        dd = DataDocument.objects.get(pk=self.dd_id)
        # et = ExtractedText.objects.get(data_document=dd)
        self.dd_pdf = dd.file.name

        in_mem_sample_csv = self.generate_valid_funcuse_csv(" surfactant; fragrance ")
        req_data = {"extfile-extraction_script": 5, "extfile-submit": "Submit"}
        req_data.update(self.mng_data)
        req_data["extfile-bulkformsetfileupload"] = in_mem_sample_csv
        self.assertEqual(
            len(ExtractedFunctionalUse.objects.filter(extracted_text_id=self.dd_id)),
            0,
            "Empty before upload.",
        )
        # Now get the response
        resp = self.c.post("/datagroup/50/", req_data)
        resp = self.get_results(resp)
        self.assertContains(resp, '"result": 1,')
        # Check the two new records
        self.assertEqual(
            FunctionalUse.objects.count(),
            2,
            "There should be two new functional use records associated with \
                the newly added ExtractedFunctionalUse record",
        )

        efu = ExtractedFunctionalUse.objects.filter(
            extracted_text_id=self.dd_id
        ).first()
        fus = FunctionalUse.objects.filter(chemicals=efu.rawchem_ptr_id)
        self.assertEquals(fus.filter(report_funcuse=" fragrance ").count(), 0)
        self.assertEquals(fus.filter(report_funcuse=" surfactant").count(), 0)
        self.assertEquals(fus.filter(report_funcuse="fragrance").count(), 1)
        self.assertEquals(fus.filter(report_funcuse="surfactant").count(), 1)

        doc_count = DataDocument.objects.filter(raw_category="raw PUC").count()
        self.assertTrue(
            doc_count > 0, "DataDocument raw category values must be updated."
        )

        self.assertEqual(
            len(ExtractedFunctionalUse.objects.filter(extracted_text_id=self.dd_id)),
            1,
            "One new ExtractedFunctionalUse after upload.",
        )

    def test_functionaluse_too_long(self):
        # Test what happens when the functional use string in the csv is too long
        # for the database field
        self.dd_id = 500
        dd = DataDocument.objects.get(pk=self.dd_id)
        # et = ExtractedText.objects.get(data_document=dd)
        self.dd_pdf = dd.file.name
        # Test a genuinely too-long field
        too_long_reported_funcuse = "funcuse" * 47
        in_mem_sample_csv = self.generate_valid_funcuse_csv(too_long_reported_funcuse)
        req_data = {"extfile-extraction_script": 5, "extfile-submit": "Submit"}
        req_data.update(self.mng_data)
        req_data["extfile-bulkformsetfileupload"] = in_mem_sample_csv
        # Now get the response
        resp = self.c.post("/datagroup/50/", req_data)
        resp = self.get_results(resp)
        self.assertContains(resp, "The reported functional use string is too long")

        # Test a field that would be too long for the model, but is getting split
        # into multiple functional uses
        too_long_reported_funcuse = "funcuse;" * 47
        in_mem_sample_csv = self.generate_valid_funcuse_csv(too_long_reported_funcuse)
        req_data = {"extfile-extraction_script": 5, "extfile-submit": "Submit"}
        req_data.update(self.mng_data)
        req_data["extfile-bulkformsetfileupload"] = in_mem_sample_csv
        # Now get the response
        resp = self.c.post("/datagroup/50/", req_data)
        resp = self.get_results(resp)
        self.assertContains(resp, '"result": 1,')

    def test_chemicalpresencelist_upload(self):
        dd_id = 254782
        dd = DataDocument.objects.get(pk=dd_id)
        dd_pdf = dd.file.name

        sample_csv = (
            "data_document_id,data_document_filename,doc_date,raw_category,raw_cas,raw_chem_name,"
            "report_funcuse,cat_code,description_cpcat,cpcat_code,cpcat_sourcetype,component"
            "\n"
            "%s,"
            "%s,"
            "2018-04-07,,,,,,,,,CP Test Component" % (dd_id, dd_pdf)
        )
        sample_csv_bytes = sample_csv.encode(encoding="UTF-8", errors="strict")
        in_mem_sample_csv = InMemoryUploadedFile(
            io.BytesIO(sample_csv_bytes),
            field_name="extfile-bulkformsetfileupload",
            name="Chemical_presence_list_template.csv",
            content_type="text/csv",
            size=len(sample_csv),
            charset="utf-8",
        )
        req_data = {"extfile-extraction_script": 5, "extfile-submit": "Submit"}
        req_data.update(self.mng_data)
        req_data["extfile-bulkformsetfileupload"] = in_mem_sample_csv
        self.assertEqual(
            len(ExtractedCPCat.objects.filter(pk=dd_id)), 0, "Empty before upload."
        )
        # Now get the response
        resp = self.c.post("/datagroup/49/", req_data)
        resp = self.get_results(resp)
        self.assertContains(resp, '"result": 1,')

        self.assertEqual(
            len(ExtractedCPCat.objects.filter(pk=dd_id)),
            1,
            "One new ExtractedCPCat after upload.",
        )

    def generate_lm_upload_request_data(self, sample_csv):
        sample_csv_bytes = sample_csv.encode(encoding="UTF-8", errors="strict")
        in_mem_sample_csv = InMemoryUploadedFile(
            io.BytesIO(sample_csv_bytes),
            field_name="extfile-bulkformsetfileupload",
            name="Chemical_presence_list_template.csv",
            content_type="text/csv",
            size=len(sample_csv),
            charset="utf-8",
        )
        req_data = {"extfile-extraction_script": 5, "extfile-submit": "Submit"}
        req_data.update(self.mng_data)
        req_data["extfile-bulkformsetfileupload"] = in_mem_sample_csv

        return req_data

    def test_literature_monitor_upload(self):
        dg = DataGroup.objects.filter(group_type__code="LM").first()
        dd = DataDocument.objects.filter(data_group=dg).first()
        lmdoc = ExtractedLMDoc(
            doc_date="2020-01-01",
            study_type="Targeted",
            media="media",
            qa_flag="qa flag",
            qa_who="qa who",
            extraction_wa="extraction wa",
        )
        lmrec = ExtractedLMRec(
            raw_chem_name="raw chem",
            raw_cas="raw cas",
            chem_detected_flag="1",
            study_location="study location",
            sampling_date="01/01/2021",
            population_description="population description",
            population_gender="F",
            population_age="adults",
            population_other="other",
            sampling_method="sampling method",
            analytical_method="analytical method",
            medium="medium",
            harmonized_medium=HarmonizedMedium.objects.first(),
            num_measure=100,
            num_nondetect=10,
            detect_freq=2.0,
            detect_freq_type="R",
            LOD=3.3,
            LOQ=4.4,
        )

        sample_csv = (
            "data_document_id,data_document_filename,doc_date,study_type,media,qa_flag,qa_who,extraction_wa,"
            "raw_chem_name,raw_cas,chem_detected_flag,study_location,sampling_date,population_description,"
            "population_gender,population_age,population_other,sampling_method,analytical_method,medium,"
            "harmonized_medium,num_measure,num_nondetect,detect_freq,detect_freq_type,LOD,LOQ,statistical_values"
            "\n"
            f"{dd.id},{dd.file.name},{lmdoc.doc_date},{lmdoc.study_type},{lmdoc.media},"
            f"{lmdoc.qa_flag},{lmdoc.qa_who},{lmdoc.extraction_wa},"
            f"{lmrec.raw_chem_name},{lmrec.raw_cas},{lmrec.chem_detected_flag},{lmrec.study_location},"
            f"{lmrec.sampling_date},{lmrec.population_description},aaaa,"
            f"{lmrec.population_age},{lmrec.population_other},{lmrec.sampling_method},{lmrec.analytical_method},"
            f"{lmrec.medium},bbbb,{lmrec.num_measure},{lmrec.num_nondetect},"
            f"{lmrec.detect_freq},cccc,{lmrec.LOD},{lmrec.LOQ},"
            "\"{'name': '', 'value': '', 'value_type': 'dddd', 'stat_unit': ''}\""
        )
        req_data = self.generate_lm_upload_request_data(sample_csv)
        # Now get the response
        resp = self.c.post(f"/datagroup/{dg.id}/", req_data)
        resp = self.get_results(resp)
        self.assertContains(resp, "aaaa is not one of the available choices")
        self.assertContains(resp, "bbbb is not one of the available choices")
        self.assertContains(resp, "cccc is not one of the available choices")
        self.assertContains(resp, "dddd is not one of the available choices")
        self.assertContains(resp, "name field is required")
        self.assertContains(resp, "value field is required")
        self.assertContains(resp, "stat_unit field is required")

        sample_csv = (
            "data_document_id,data_document_filename,doc_date,study_type,media,qa_flag,qa_who,extraction_wa,"
            "raw_chem_name,raw_cas,chem_detected_flag,study_location,sampling_date,population_description,"
            "population_gender,population_age,population_other,sampling_method,analytical_method,medium,"
            "harmonized_medium,num_measure,num_nondetect,detect_freq,detect_freq_type,LOD,LOQ,statistical_values"
            "\n"
            f"{dd.id},{dd.file.name},{lmdoc.doc_date},{lmdoc.study_type},{lmdoc.media},"
            f"{lmdoc.qa_flag},{lmdoc.qa_who},{lmdoc.extraction_wa},"
            f"chem1,{lmrec.raw_cas},{lmrec.chem_detected_flag},{lmrec.study_location},"
            f"{lmrec.sampling_date},{lmrec.population_description},{lmrec.population_gender},"
            f"{lmrec.population_age},{lmrec.population_other},{lmrec.sampling_method},{lmrec.analytical_method},"
            f"{lmrec.medium},{lmrec.harmonized_medium.name},{lmrec.num_measure},{lmrec.num_nondetect},"
            f"{lmrec.detect_freq},{lmrec.detect_freq_type},{lmrec.LOD},{lmrec.LOQ},"
            "\"{'name': 'median', 'value': '1.1', 'value_type': 'R', 'stat_unit': 'mg/L'};"
            "{'name': 'mean', 'value': 2.2, 'value_type': 'C', 'stat_unit': 'mg/L'}\""
            "\n"
            f"{dd.id},{dd.file.name},{lmdoc.doc_date},{lmdoc.study_type},{lmdoc.media},"
            f"{lmdoc.qa_flag},{lmdoc.qa_who},{lmdoc.extraction_wa},"
            "chem2,,,,,,,,,,,,,,,,,,,"
            "\n"
            f"{dd.id},{dd.file.name},{lmdoc.doc_date},{lmdoc.study_type},{lmdoc.media},"
            f"{lmdoc.qa_flag},{lmdoc.qa_who},{lmdoc.extraction_wa},"
            f"chem3,{lmrec.raw_cas},{lmrec.chem_detected_flag},{lmrec.study_location},"
            f"{lmrec.sampling_date},{lmrec.population_description},{lmrec.population_gender},"
            f"{lmrec.population_age},{lmrec.population_other},{lmrec.sampling_method},{lmrec.analytical_method},"
            f"{lmrec.medium},{lmrec.harmonized_medium.name},{lmrec.num_measure},{lmrec.num_nondetect},"
            f"{lmrec.detect_freq},{lmrec.detect_freq_type},{lmrec.LOD},{lmrec.LOQ},"
            "\"{'name': 'mean', 'value': 3, 'value_type': 'computed', 'stat_unit': 'mg/L'}\""
        )
        req_data = self.generate_lm_upload_request_data(sample_csv)
        # Now get the response
        resp = self.c.post(f"/datagroup/{dg.id}/", req_data)
        resp = self.get_results(resp)
        self.assertContains(resp, '"result": 3,')

        doc = ExtractedLMDoc.objects.filter(data_document=dd, media="media").first()
        self.assertIsNotNone(doc)
        self.assertEquals(lmdoc.doc_date, doc.doc_date)
        self.assertEquals(lmdoc.study_type, doc.study_type)
        self.assertEquals(lmdoc.qa_flag, doc.qa_flag)
        self.assertEquals(lmdoc.qa_who, doc.qa_who)
        self.assertEquals(lmdoc.extraction_wa, doc.extraction_wa)

        # confirm that a duplicate ExtractedComposition record is not
        # being generated
        self.assertEqual(
            ExtractedComposition.objects.filter(extracted_text_id=dd.id).count(), 0
        )

        chem1 = ExtractedLMRec.objects.filter(
            raw_chem_name="chem1", extracted_text_id=dd.id
        ).first()
        self.assertIsNotNone(chem1)
        self.assertEquals(lmrec.raw_cas, chem1.raw_cas)
        self.assertEquals(lmrec.chem_detected_flag, chem1.chem_detected_flag)
        self.assertEquals(lmrec.study_location, chem1.study_location)
        self.assertEquals(lmrec.sampling_date, chem1.sampling_date.strftime("%m/%d/%Y"))
        self.assertEquals(lmrec.population_description, chem1.population_description)
        self.assertEquals(lmrec.sampling_method, chem1.sampling_method)
        self.assertEquals(lmrec.analytical_method, chem1.analytical_method)
        self.assertEquals(lmrec.medium, chem1.medium)
        self.assertEquals(lmrec.harmonized_medium, chem1.harmonized_medium)
        self.assertEquals(lmrec.num_measure, chem1.num_measure)
        self.assertEquals(lmrec.num_nondetect, chem1.num_nondetect)
        self.assertEquals(lmrec.detect_freq, chem1.detect_freq)
        self.assertEquals(lmrec.detect_freq_type, chem1.detect_freq_type)
        self.assertEquals(lmrec.LOD, chem1.LOD)
        self.assertEquals(lmrec.LOQ, chem1.LOQ)

        stats1 = StatisticalValue.objects.filter(rawchem_id=chem1.rawchem_ptr_id)
        self.assertEquals(2, stats1.count())
        stat_value = stats1.first()
        self.assertEquals(stat_value.name, "median")
        self.assertEquals(stat_value.value, 1.1)
        self.assertEquals(stat_value.value_type, "R")
        self.assertEquals(stat_value.stat_unit, "mg/L")

        chem2 = ExtractedLMRec.objects.filter(
            raw_chem_name="chem2", extracted_text_id=dd.id
        ).first()
        self.assertIsNotNone(chem2)
        self.assertEquals("", chem2.raw_cas)
        self.assertIsNone(chem2.chem_detected_flag)
        self.assertIsNone(chem2.study_location)
        self.assertIsNone(chem2.sampling_date)
        self.assertIsNone(chem2.population_description)
        self.assertIsNone(chem2.sampling_method)
        self.assertIsNone(chem2.analytical_method)
        self.assertIsNone(chem2.medium)
        self.assertIsNone(chem2.harmonized_medium)
        self.assertIsNone(chem2.num_measure)
        self.assertIsNone(chem2.num_nondetect)
        self.assertIsNone(chem2.detect_freq)
        self.assertIsNone(chem2.detect_freq_type)
        self.assertIsNone(chem2.LOD)
        self.assertIsNone(chem2.LOQ)
        stats2 = StatisticalValue.objects.filter(rawchem_id=chem2.rawchem_ptr_id)
        self.assertEquals(0, stats2.count())

        chem3 = ExtractedLMRec.objects.filter(
            raw_chem_name="chem3", extracted_text_id=dd.id
        ).first()
        self.assertIsNotNone(chem3)
        self.assertEquals(lmrec.raw_cas, chem3.raw_cas)
        self.assertEquals(lmrec.chem_detected_flag, chem3.chem_detected_flag)
        self.assertEquals(lmrec.study_location, chem3.study_location)
        self.assertEquals(lmrec.sampling_date, chem3.sampling_date.strftime("%m/%d/%Y"))
        self.assertEquals(lmrec.population_description, chem3.population_description)
        self.assertEquals(lmrec.sampling_method, chem3.sampling_method)
        self.assertEquals(lmrec.analytical_method, chem3.analytical_method)
        self.assertEquals(lmrec.medium, chem3.medium)
        self.assertEquals(lmrec.harmonized_medium, chem3.harmonized_medium)
        self.assertEquals(lmrec.num_measure, chem3.num_measure)
        self.assertEquals(lmrec.num_nondetect, chem3.num_nondetect)
        self.assertEquals(lmrec.detect_freq, chem3.detect_freq)
        self.assertEquals(lmrec.detect_freq_type, chem3.detect_freq_type)
        self.assertEquals(lmrec.LOD, chem3.LOD)
        self.assertEquals(lmrec.LOQ, chem3.LOQ)

        stats3 = StatisticalValue.objects.filter(rawchem_id=chem3.rawchem_ptr_id)
        self.assertEquals(1, stats3.count())
        stat_value = stats3.first()
        self.assertEquals(stat_value.name, "mean")
        self.assertEquals(stat_value.value, 3)
        self.assertEquals(stat_value.value_type, "C")
        self.assertEquals(stat_value.stat_unit, "mg/L")
