import crum
import io
from urllib import parse

from django.test import RequestFactory, Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import InMemoryUploadedFile

from celery.result import AsyncResult
from celery_djangotest.unit import TransactionTestCase

from dashboard.models import (
    DataDocument,
    DataGroup,
    ExtractedComposition,
    ExtractedCPCat,
    ExtractedListPresence,
    ExtractedFunctionalUse,
    AuditLog,
    FunctionalUse,
    FunctionalUseCategory,
    RawChem,
    ExtractedText,
    Script,
)
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


class AuditLogTest(TempFileMixin, TransactionTestCase):
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
        self.user = User.objects.get(username="Karyn")
        self.c.force_login(self.user)

    def generate_valid_chem_csv(self):
        csv_string = (
            "data_document_id,data_document_filename,"
            "prod_name,doc_date,rev_num,raw_category,raw_cas,raw_chem_name,"
            "report_funcuse,raw_min_comp,raw_max_comp,unit_type,"
            "ingredient_rank,raw_central_comp,component"
            "\n"
            "8,11177849.pdf,Alberto European Hairspray (Aerosol) - All Variants,,,aerosol hairspray,"
            "0000075-37-6,hydrofluorocarbon 152a (difluoroethane),,0.39,0.42,2,,,Test Component"
            "\n"
            "7,11165872.pdf,Alberto European Hairspray (Aerosol) - All Variants,,,aerosol hairspray,"
            "0000064-17-5,sd alcohol 40-b (ethanol),,0.5,0.55,2,,,Test Component"
            "\n"
            "7,11165872.pdf,Alberto European Hairspray (Aerosol) - All Variants,,,aerosol hairspray,"
            "0000064-17-6,sd alcohol 40-c (ethanol c),,,,2,,,Test Component"
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

    def test_audit_log_chem_upload(self):
        req_data = {
            "extfile-extraction_script": 5,
            "extfile-weight_fraction_type": 1,
            "extfile-submit": "Submit",
            "extfile-bulkformsetfileupload": self.generate_valid_chem_csv(),
        }
        req_data.update(self.mng_data)
        with crum.impersonate(self.user):
            resp = self.c.post("/datagroup/6/", req_data)
        task_id = parse.parse_qs(parse.urlparse(resp.url).query)["task_id"][0]
        AsyncResult(task_id).wait()

        # get audit logs
        logs = AuditLog.objects.all()
        self.assertEquals(16, len(logs), "Should have log entries")

        for log in logs:
            self.assertIsNotNone(log.model_name)
            self.assertIsNotNone(log.field_name)
            self.assertIsNone(log.old_value)
            self.assertTrue(log.new_value)
            self.assertIsNotNone(log.date_created)
            self.assertIsNotNone(log.user_id)
            self.assertEquals("I", log.action, "Should be Insert action")

        logs.delete()

        # bulk update fields for 3 chemicals
        chems = ExtractedComposition.objects.filter(component="Test Component")

        funcuse = FunctionalUse(report_funcuse="report func use")
        funcuse.save()
        for chemical in chems:
            chemical.raw_min_comp = "min comp"
            chemical.raw_max_comp = "max comp"
            chemical.raw_central_comp = "central comp"
            chemical.unit_type_id = 1
            chemical.ingredient_rank = 5
            chemical.lower_wf_analysis = 0.01
            chemical.central_wf_analysis = 0.44
            chemical.upper_wf_analysis = 0.88
            chemical.save()
            chemical.functional_uses.add(funcuse)

        logs = AuditLog.objects.all()
        self.assertEquals(27, len(logs), "Should have 27 log entries")
        self.assertEquals(3, sum(log.field_name == "raw_min_comp" for log in logs))
        self.assertEquals(3, sum(log.field_name == "raw_max_comp" for log in logs))
        self.assertEquals(3, sum(log.field_name == "raw_central_comp" for log in logs))
        self.assertEquals(3, sum(log.field_name == "unit_type_id" for log in logs))
        self.assertEquals(3, sum(log.field_name == "report_funcuse" for log in logs))
        self.assertEquals(3, sum(log.field_name == "ingredient_rank" for log in logs))
        self.assertEquals(3, sum(log.field_name == "upper_wf_analysis" for log in logs))
        self.assertEquals(
            3, sum(log.field_name == "central_wf_analysis" for log in logs)
        )
        self.assertEquals(3, sum(log.field_name == "lower_wf_analysis" for log in logs))

        for log in logs:
            self.assertIn(
                log.model_name, ("functionalusetorawchem", "extractedcomposition")
            )
            self.assertIsNotNone(log.object_key)
            self.assertIsNotNone(log.field_name)
            self.assertIsNotNone(log.new_value)
            self.assertIsNotNone(log.date_created)
            self.assertIsNotNone(log.user_id)
            if log.model_name == "functionalusetorawchem":
                self.assertEquals("I", log.action, "Should be Insert action")
            else:
                self.assertEquals("U", log.action, "Should be Update action")
        logs.delete()

        # change rid
        for chem in chems:
            chem.rid = "test rid"
            chem.save()
        logs = AuditLog.objects.all()
        self.assertEquals(3, len(logs), "Should have log entries")
        for log in logs:
            self.assertEquals(log.model_name, "rawchem")
            self.assertEquals("rid", log.field_name)
            self.assertFalse(log.old_value)
            self.assertEquals("test rid", log.new_value)
            self.assertIsNotNone(log.date_created)
            self.assertIsNotNone(log.user_id)
            self.assertEquals("U", log.action, "Should be Update action")
        logs.delete()

        # change component
        for chem in chems:
            chem.component = "A Changed Test Component"
            chem.save()
        logs = AuditLog.objects.all()
        self.assertEquals(3, len(logs), "Should have log entries")
        for log in logs:
            self.assertEquals(log.model_name, "rawchem")
            self.assertEquals("component", log.field_name)
            self.assertEquals("Test Component", log.old_value)
            self.assertEquals("A Changed Test Component", log.new_value)
            self.assertIsNotNone(log.date_created)
            self.assertIsNotNone(log.user_id)
            self.assertEquals("U", log.action, "Should be Update action")
        logs.delete()

        # delete chemicals
        for chemical in chems:
            chemical.delete()

        logs = AuditLog.objects.all()
        self.assertEquals(39, len(logs), "Should have 39 log entries")
        self.assertEquals(3, sum(log.field_name == "raw_min_comp" for log in logs))
        self.assertEquals(3, sum(log.field_name == "raw_max_comp" for log in logs))
        self.assertEquals(3, sum(log.field_name == "raw_central_comp" for log in logs))
        self.assertEquals(3, sum(log.field_name == "unit_type_id" for log in logs))
        self.assertEquals(3, sum(log.field_name == "report_funcuse" for log in logs))
        self.assertEquals(3, sum(log.field_name == "ingredient_rank" for log in logs))
        self.assertEquals(3, sum(log.field_name == "upper_wf_analysis" for log in logs))
        self.assertEquals(
            3, sum(log.field_name == "central_wf_analysis" for log in logs)
        )
        self.assertEquals(3, sum(log.field_name == "lower_wf_analysis" for log in logs))
        self.assertEquals(3, sum(log.field_name == "raw_cas" for log in logs))
        self.assertEquals(3, sum(log.field_name == "raw_chem_name" for log in logs))
        self.assertEquals(3, sum(log.field_name == "rid" for log in logs))
        self.assertEquals(3, sum(log.field_name == "component" for log in logs))
        for log in logs:
            self.assertIsNotNone(log.object_key)
            self.assertIsNotNone(log.model_name)
            self.assertIsNotNone(log.field_name)
            self.assertIsNone(log.new_value)
            self.assertIsNotNone(log.old_value)
            self.assertIsNotNone(log.date_created)
            self.assertIsNotNone(log.user_id)
            self.assertEquals("D", log.action, "Should be Delete action")
        logs.delete()

        dg = DataGroup.objects.get(pk=6)
        dg.delete()

    def test_audit_log_presence_upload(self):
        # Delete the CPCat records that were loaded with the fixtures
        ExtractedCPCat.objects.all().delete()
        self.assertEqual(
            len(ExtractedCPCat.objects.all()), 0, "Should be empty before upload."
        )

        # upload file
        in_mem_sample_csv = make_upload_csv("sample_files/presence_good.csv")
        req_data = {
            "extfile-extraction_script": 5,
            "extfile-submit": "Submit",
            "extfile-bulkformsetfileupload": in_mem_sample_csv,
        }
        req_data.update(self.mng_data)
        with crum.impersonate(self.user):
            resp = self.c.post("/datagroup/49/", req_data)
        task_id = parse.parse_qs(parse.urlparse(resp.url).query)["task_id"][0]
        AsyncResult(task_id).wait()

        logs = AuditLog.objects.all()
        self.assertEquals(14, len(logs), "Should have log entries")

        for log in logs:
            self.assertIsNotNone(log.model_name)
            self.assertIsNotNone(log.field_name)
            self.assertIsNone(log.old_value)
            self.assertTrue(log.new_value)
            self.assertIsNotNone(log.date_created)
            self.assertIsNotNone(log.user_id)
            self.assertEquals("I", log.action, "Should be Insert action")
        logs.delete()

        # update
        chems = ExtractedListPresence.objects.all()
        for chem in chems:
            chem.raw_cas = "test raw cas"
            chem.raw_chem_name = "test raw chem name"
            chem.report_funcuse = "report func use"
            chem.save()

        logs = AuditLog.objects.all()
        self.assertEquals(6, len(logs), "Should have 6 log entries")

        for log in logs:
            self.assertIsNotNone(log.model_name)
            self.assertIsNotNone(log.field_name)
            self.assertIsNotNone(log.new_value)
            self.assertIsNotNone(log.date_created)
            self.assertIsNotNone(log.user_id)
            self.assertEquals("U", log.action, "Should be Update action")
        logs.delete()

        # delete
        chems.delete()

        logs = AuditLog.objects.all()
        self.assertEquals(14, len(logs), "Should have log entries")

        for log in logs:
            self.assertIsNotNone(log.model_name)
            self.assertIsNotNone(log.field_name)
            self.assertIsNotNone(log.old_value)
            self.assertIsNone(log.new_value)
            self.assertIsNotNone(log.date_created)
            self.assertIsNotNone(log.user_id)
            self.assertEquals("D", log.action, "Should be Delete action")

        dg = DataGroup.objects.get(pk=49)
        dg.delete()

    def test_audit_log_functionaluse_upload(self):
        dd_id = 500
        dd = DataDocument.objects.get(pk=dd_id)
        dd_pdf = dd.file.name

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
            "surfactant" % (dd_id, dd_pdf)
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
        req_data = {
            "extfile-extraction_script": 5,
            "extfile-submit": "Submit",
            "extfile-bulkformsetfileupload": in_mem_sample_csv,
        }
        req_data.update(self.mng_data)
        with crum.impersonate(self.user):
            resp = self.c.post("/datagroup/50/", req_data)
        task_id = parse.parse_qs(parse.urlparse(resp.url).query)["task_id"][0]
        AsyncResult(task_id).wait()

        self.assertEqual(
            len(ExtractedFunctionalUse.objects.filter(extracted_text_id=dd_id)),
            1,
            "One new ExtractedFunctionalUse after upload.",
        )

        logs = AuditLog.objects.all()
        self.assertEquals(3, len(logs), "Should have log entries")
        for log in logs:
            self.assertIsNotNone(log.model_name)
            self.assertIsNotNone(log.field_name)
            self.assertIsNone(log.old_value)
            self.assertIsNotNone(log.new_value)
            self.assertIsNotNone(log.date_created)
            self.assertIsNotNone(log.user_id)
            self.assertEquals("I", log.action, "Should be Insert action")
        logs.delete()

        # add a related FunctionalUse record
        efs = ExtractedFunctionalUse.objects.filter(extracted_text_id=dd_id)
        for ef in efs:
            efu = FunctionalUse(report_funcuse="test func use")
            efu.save()
            ef.functional_uses.add(efu)

        logs = AuditLog.objects.all()
        self.assertEquals(
            1, len(logs), "Should have a log entry for new functional use"
        )
        for log in logs.filter(field_name="report_funcuse"):
            self.assertEquals(log.model_name, "functionalusetorawchem")
            self.assertIsNotNone(log.new_value)
            self.assertEquals(log.new_value, "test func use")
            self.assertIsNotNone(log.date_created)
            self.assertIsNotNone(log.user_id)
            self.assertEquals("I", log.action, "Should be Insert action")
        logs.delete()

        # delete
        for ef in efs:
            ef.delete()
        logs = AuditLog.objects.all()
        self.assertEquals(4, len(logs), "Should have log entries")
        for log in logs:
            self.assertIsNotNone(log.model_name)
            self.assertIsNotNone(log.field_name)
            self.assertIsNotNone(log.old_value)
            self.assertIsNone(log.new_value)
            self.assertIsNotNone(log.date_created)
            self.assertIsNotNone(log.user_id)
            self.assertEquals("D", log.action, "Should be delete action")

        # delete data document should cascade delete all auditlogs
        dd = DataDocument.objects.get(pk=dd_id)
        auditlogs = AuditLog.objects.filter(extracted_text_id=dd_id)

        self.assertIsNotNone(dd)
        self.assertTrue(auditlogs.count() > 0)

        dd.delete()
        auditlogs = AuditLog.objects.filter(extracted_text_id=dd_id)
        self.assertTrue(auditlogs.count() == 0)

    def test_functional_use_audit_logs(self):
        ext = ExtractedText.objects.create(
            data_document=DataDocument.objects.first(),
            extraction_script=Script.objects.first(),
        )
        chem = RawChem.objects.create(extracted_text=ext)
        cat1 = FunctionalUseCategory.objects.create(
            title="cat1", description="test category 1"
        )
        cat2 = FunctionalUseCategory.objects.create(
            title="cat2", description="test category 2"
        )
        fu1 = FunctionalUse.objects.create(report_funcuse="fu1", category=cat1)
        fu2 = FunctionalUse.objects.create(report_funcuse="fu2", category=cat2)
        AuditLog.objects.all().delete()

        # add fu to chem
        chem.functional_uses.add(fu1)
        chem.save()
        rfu = AuditLog.objects.filter(field_name="report_funcuse")
        self.assertEqual(1, rfu.count())
        hc = AuditLog.objects.filter(field_name="harmonized category")
        self.assertEqual(1, hc.count())

        # update fu reported field
        AuditLog.objects.all().delete()
        fu1.report_funcuse = "updated"
        fu1.save()
        rfu = AuditLog.objects.filter(field_name="report_funcuse")
        self.assertEqual(1, rfu.count())
        hc = AuditLog.objects.filter(field_name="harmonized category")
        self.assertEqual(0, hc.count())

        # update fu category
        AuditLog.objects.all().delete()
        fu1.category = cat2
        fu1.save()
        rfu = AuditLog.objects.filter(field_name="report_funcuse")
        self.assertEqual(0, rfu.count())
        hc = AuditLog.objects.filter(field_name="harmonized category")
        self.assertEqual(1, hc.count())

        # update category title
        AuditLog.objects.all().delete()
        cat2.title = "updated title"
        cat2.save()
        rfu = AuditLog.objects.filter(field_name="report_funcuse")
        self.assertEqual(0, rfu.count())
        hc = AuditLog.objects.filter(field_name="harmonized category")
        self.assertEqual(1, hc.count())

        # delete fu category
        AuditLog.objects.all().delete()
        fu1.category = None
        fu1.save()
        rfu = AuditLog.objects.filter(field_name="report_funcuse")
        self.assertEqual(0, rfu.count())
        hc = AuditLog.objects.filter(field_name="harmonized category")
        self.assertEqual(1, hc.count())

        # change chem fu
        AuditLog.objects.all().delete()
        chem.functional_uses.remove(fu1)
        chem.functional_uses.add(fu2)
        chem.save()
        rfu = AuditLog.objects.filter(field_name="report_funcuse")
        self.assertEqual(2, rfu.count())
        hc = AuditLog.objects.filter(field_name="harmonized category")
        self.assertEqual(1, hc.count())

        # delete chem fu
        AuditLog.objects.all().delete()
        chem.functional_uses.clear()
        chem.save()
        rfu = AuditLog.objects.filter(field_name="report_funcuse")
        self.assertEqual(1, rfu.count())
        hc = AuditLog.objects.filter(field_name="harmonized category")
        self.assertEqual(1, hc.count())
