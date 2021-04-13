import csv
import io
import os
from unittest import skip

from django.core.files import File
from django.core.exceptions import ValidationError
from django.test import TestCase, tag
from django.db.utils import IntegrityError
from django.db.models import Count, Q
from dashboard.models import *
from dashboard.tests.loader import *
from dashboard.tests.mixins import TempFileMixin


def create_data_documents(data_group, source_type, pdfs):
    """Used to imitate the creation of new DataDocuments from CSV"""
    dds = []
    with open("./sample_files/register_records_matching.csv", "r") as dg_csv:
        table = csv.DictReader(dg_csv)
        for line in table:  # read every csv line, create docs for each
            if line["title"] == "":  # updates title in line object
                line["title"] = line["filename"].split(".")[0]
            _, ext = os.path.splitext(line["filename"])
            file = (
                File(io.BytesIO(), name="blank{ext}")
                if line["filename"] in pdfs
                else None
            )
            dd = DataDocument.objects.create(
                filename=line["filename"],
                file=file,
                title=line["title"],
                document_type=DocumentType.objects.get(code="MS"),
                url=line["url"],
                organization=line["organization"],
                data_group=data_group,
            )
            dd.save()
            dds.append(dd)
        return dds


def create_data_documents_with_txt(data_group, source_type, pdf_txt):
    """Used to imitate the creation of new DataDocuments from CSV"""
    dds = []
    with open("./sample_files/register_records_matching_with_txt.csv", "r") as dg_csv:
        table = csv.DictReader(dg_csv)
        for line in table:  # read every csv line, create docs for each
            if line["title"] == "":  # updates title in line object
                line["title"] = line["filename"].split(".")[0]
            _, ext = os.path.splitext(line["filename"])
            file = (
                File(io.BytesIO(), name=f"blank{ext}")
                if line["filename"] in pdf_txt
                else None
            )
            dd = DataDocument.objects.create(
                filename=line["filename"],
                file=file,
                title=line["title"],
                document_type=DocumentType.objects.get(code="MS"),
                url=line["url"],
                organization=line["organization"],
                data_group=data_group,
            )
            dd.save()
            dds.append(dd)
        return dds


@tag("loader")
class ModelsTest(TempFileMixin, TestCase):
    def setUp(self):
        self.objects = load_model_objects()
        self.client.login(username="Karyn", password="specialP@55word")
        self.pdfs = [
            "0bf5755e-3a08-4024-9d2f-0ea155a9bd17.pdf",
            "0c68ab16-2065-4d9b-a8f2-e428eb192465.pdf",
        ]
        self.pdf_txt = [
            "0bf5755e-3a08-4024-9d2f-0ea155a9bd17.pdf",
            "0bf5755e-3a08-4024-9d2f-0ea155a9bd17.txt",
        ]

    def test_object_creation(self):
        self.assertTrue(isinstance(self.objects.ds, DataSource))
        self.assertTrue(isinstance(self.objects.script, Script))
        self.assertTrue(isinstance(self.objects.extext, ExtractedText))
        self.assertTrue(isinstance(self.objects.ec, ExtractedComposition))
        self.assertTrue(isinstance(self.objects.p, Product))
        self.assertTrue(isinstance(self.objects.pd, ProductDocument))
        self.assertTrue(isinstance(self.objects.pt, PUCTag))

    def test_datagroup(self):
        self.assertTrue(isinstance(self.objects.dg, DataGroup))

        self.assertEqual(str(self.objects.dg), self.objects.dg.name)
        self.assertEqual("https://www.epa.gov", self.objects.dg.url)

    @tag("puc")
    def test_object_properties(self):
        # Test properties of objects
        # DataSource
        self.assertEqual(str(self.objects.ds), self.objects.ds.title)
        self.assertTrue(hasattr(PUCToTag, "assumed"))
        # DataDocuments
        # Confirm that one of the data documents appears in the data group
        # show page after upload from CSV
        docs = create_data_documents(self.objects.dg, self.objects.st, self.pdfs)
        self.assertEqual(len(docs), 2, ("Only 2 records should be created!"))
        dg_response = self.client.get(
            f"/datagroup/{str(self.objects.dg.pk)}/documents_table/"
        )
        self.assertIn(b"NUTRA", dg_response.content)
        self.assertEqual(len(self.pdfs), 2)
        # Confirm that the two data documents in the csv file are matches to
        # the pdfs via their file names
        self.assertEqual(self.objects.dg.matched_docs(), 2)
        # DownloadScript
        self.assertEqual(str(self.objects.script), "Test Download Script")
        # ExtractedText
        self.assertEqual(str(self.objects.extext), "test document")
        # RawChem
        self.assertEqual(str(self.objects.rc), "Test Chem Name")
        # ExtractedComposition
        self.assertEqual(str(self.objects.ec), "Test Chem Name")

    def test_product_attribute(self):
        self.assertEqual(ProductToTag.objects.count(), 0)
        p2t = ProductToTag.objects.create(
            content_object=self.objects.p, tag=self.objects.pt
        )
        self.assertEqual(ProductToTag.objects.count(), 1)

    def test_data_group(self):
        doc = DataDocument.objects.create(data_group=self.objects.dg)
        self.assertFalse(self.objects.dg.all_matched())
        self.assertFalse(self.objects.dg.all_extracted())
        doc.save()
        self.assertFalse(self.objects.dg.all_matched())
        for doc in self.objects.dg.datadocument_set.all():
            doc.file = File(io.BytesIO(), name="blank.pdf")
            doc.save()
        self.assertTrue(self.objects.dg.all_matched())

    @tag("puc")
    def test_extracted_habits_and_practices(self):
        puc2 = PUC.objects.create(
            gen_cat="Test General Category",
            prod_fam="Test Product Family",
            prod_type="Test Product Type",
            description="Test Product Description",
            last_edited_by=self.objects.user,
        )
        self.assertEqual(ExtractedHabitsAndPractices.objects.count(), 1)
        self.assertEqual(ExtractedHabitsAndPracticesDataType.objects.count(), 1)
        self.assertEqual(ExtractedHabitsAndPracticesToPUC.objects.count(), 0)
        e2p = ExtractedHabitsAndPracticesToPUC.objects.create(
            extracted_habits_and_practices=self.objects.ehp, PUC=self.objects.puc
        )
        e2p = ExtractedHabitsAndPracticesToPUC.objects.create(
            extracted_habits_and_practices=self.objects.ehp, PUC=puc2
        )
        self.assertEqual(ExtractedHabitsAndPracticesToPUC.objects.count(), 2)

    def test_data_document_organization(self):
        self.assertEqual(self.objects.doc.organization, "")
        self.objects.doc.organization = "Test Organization"
        self.objects.doc.save()
        self.assertEqual(
            DataDocument.objects.filter(organization="Test Organization").count(), 1
        )

    def test_dg_with_txt(self):
        # Test properties of objects
        # DataSource
        self.assertEqual(str(self.objects.ds), self.objects.ds.title)

        # DataDocuments
        # Confirm that one of the data documents appears in the data group
        # show page after upload from CSV
        docs = create_data_documents_with_txt(
            self.objects.dg, self.objects.st, self.pdf_txt
        )
        self.assertEqual(len(docs), 2, ("Only 2 records should be created!"))
        dg_response = self.client.get(
            f"/datagroup/{str(self.objects.dg.pk)}/documents_table/"
        )
        self.assertIn(b"NUTRA", dg_response.content)
        self.assertEqual(len(self.pdf_txt), 2)
        # Confirm that the two data documents in the csv file are matches to
        # the pdfs via their file names
        self.assertEqual(self.objects.dg.matched_docs(), 2)

    def test_script_fields(self):
        fields = ["title", "url", "qa_begun", "script_type", "confidence"]
        for fld in fields:
            self.assertIn(
                fld, Script.__dict__, (f"{fld} " "should be in Script model.")
            )
        url = next(f for f in Script._meta.fields if f.name == "url")
        self.assertTrue(
            url.max_length == 225, ("'url' field should be of " "length 225")
        )

    def test_taxonomy_fields(self):
        fields = [
            "title",
            "description",
            "parent",
            "source",
            "category_code",
            "last_edited_by",
            "created_at",
            "updated_at",
        ]
        taxonomy_fields = [f.name for f in Taxonomy._meta.fields]
        for fld in fields:
            self.assertIn(
                fld, taxonomy_fields, (f"{fld} " "should be in Taxonomy model.")
            )
        title = next(f for f in Taxonomy._meta.fields if f.name == "title")
        self.assertTrue(
            title.max_length == 250, ("'title' field should have " "max length of 250")
        )

    def test_LP_keyword_fields(self):
        fields = [fld.name for fld in ExtractedListPresenceTag._meta.fields]
        for fld in ["name", "slug", "definition", "kind"]:
            self.assertIn(
                fld, fields, f"{fld} should be in ExtractedListPresenceTag model."
            )


class ModelTestWithFixtures(TestCase):

    fixtures = fixtures_standard

    def test_puc_fields(self):
        fields = [
            "kind",
            "gen_cat",
            "prod_fam",
            "prod_type",
            "description",
            "last_edited_by",
            "products",
            "extracted_habits_and_practices",
            "tags",
        ]
        model_fields = [f.name for f in PUC._meta.get_fields()]
        for fld in fields:
            self.assertIn(fld, model_fields, f'"{fld}"" field should be in PUC model.')

    @tag("puc")
    def test_puctag_fields(self):
        fields = ["name", "slug", "definition"]
        model_fields = [f.name for f in PUCTag._meta.get_fields()]
        for fld in fields:
            self.assertIn(
                fld, model_fields, f'"{fld}"" field should be in PUCTag model.'
            )

    @tag("puc")
    def test_puc_get_children(self):
        """Level 1 and 2 PUCs should accumulate lower level PUCs.
        """
        puc = PUC.objects.get(pk=20)  # PUC w/ only gen_cat value
        self.assertGreater(
            len(puc.get_children()), 1, ("PUC should have more than one child PUCs")
        )
        puc = PUC.objects.get(pk=6)  # PUC w/ gen_cat and prod_fam value
        self.assertGreater(
            len(puc.get_children()), 1, ("PUC should have more than one child PUCs")
        )
        puc = PUC.objects.get(pk=126)  # PUC w/ ALL values
        self.assertEqual(
            len(puc.get_children()), 1, ("PUC should only have itself associated")
        )

    @tag("puc")
    def test_puc_category_defaults(self):
        """Assert that the prod_fam and prod_type are nulled w/ an
        empty string and not NULL.
        """
        k = User.objects.get(username="Karyn")
        puc = PUC.objects.create(last_edited_by=k)
        self.assertTrue(puc.prod_fam == "")
        self.assertTrue(puc.prod_type == "")

    @tag("puc")
    def test_product_counts(self):
        """Make sure the product_count property
        returns the same thing as the num_products annotation"""
        pucs = PUC.objects.all().annotate(num_products=Count("products"))
        # pucs 1-3 have products associated with them
        self.assertEqual(
            pucs.get(pk=1).num_products, PUC.objects.get(pk=1).product_count
        )

    @tag("puc")
    def test_puc_document_counts(self):
        """Make sure that documents with multiple product linkages
        are not being double-counted."""
        puc = PUC.objects.get(pk=185)
        docs = DataDocument.objects.filter(Q(products__product_uber_puc__puc=puc))
        distinct_doc_count = docs.count()
        self.assertEqual(puc.document_count, distinct_doc_count)

    def test_datadocument_note(self):
        datadocument = DataDocument(
            filename="MyFile.pdf",
            title="My Title",
            data_group=DataGroup.objects.first(),
            note="Some long note.",
        )
        datadocument.save()
        self.assertTrue(datadocument.note, "Some long note.")

    def test_document_type_unique_title(self):
        doctype = DocumentType.objects.first()
        new_doctype = DocumentType(title=doctype.title, code="YO")
        err_msg = (
            "DocumentType was saved with duplicate title,"
            " but this field should be unique"
        )
        self.assertRaises(IntegrityError, new_doctype.save, err_msg)

    def test_document_type_unique_code(self):
        doctype = DocumentType.objects.first()
        new_doctype = DocumentType(title="lol", code=doctype.code)
        err_msg = (
            "DocumentType was saved with duplicate code,"
            " but this field should be unique"
        )
        self.assertRaises(IntegrityError, new_doctype.save, err_msg)

    def test_document_type_rm_signal(self):
        document_type_id = 15
        group_type_id = 7
        qs = DataDocument.objects.filter(
            document_type_id=document_type_id, data_group__group_type__id=group_type_id
        )
        qs_exclude = DataDocument.objects.exclude(
            document_type_id=document_type_id, data_group__group_type__id=group_type_id
        )
        num_doc_pre_rm = qs.count()
        num_ex_doc_pre_rm = qs_exclude.count()
        self.assertTrue(
            num_doc_pre_rm > 0, "Expected at least one initial valid DataDocument"
        )
        (
            DocumentTypeGroupTypeCompatibilty.objects.get(
                document_type_id=document_type_id, group_type_id=group_type_id
            ).delete()
        )
        num_doc_post_rm = qs.count()
        num_ex_doc_post_rm = qs_exclude.count()
        self.assertTrue(num_doc_post_rm == 0, "post_delete signal not received")
        self.assertTrue(
            num_ex_doc_post_rm == num_ex_doc_pre_rm + num_doc_pre_rm,
            "Too many DataDocument.document_types nullified",
        )

    def test_funcuse_fields(self):
        fields = [
            "chemicals",
            "category",
            "report_funcuse",
            "extraction_script",
            "category",
        ]
        model_fields = [f.name for f in FunctionalUse._meta.get_fields()]
        for fld in fields:
            self.assertIn(
                fld, model_fields, f'"{fld}"" field should be in FunctionalUse model.'
            )

    def test_functionaluse_update(self):
        # read
        fc = FunctionalUse.objects.filter(pk=1).first()
        self.assertEquals(fc.report_funcuse, "swell")
        self.assertIsNotNone(fc.category)
        self.assertEquals(1, fc.category.id)

        # update
        fc.report_funcuse = "report use"
        fc.category = FunctionalUseCategory(id=2)
        fc.save()
        fc = FunctionalUse.objects.filter(pk=1).first()
        self.assertEquals(fc.report_funcuse, "report use")
        self.assertEquals(2, fc.category.id)

    @skip("There is no blank constraint on report_funcuse")
    def test_functionaluse_validation(self):
        funcuse = FunctionalUse(report_funcuse="")
        self.assertRaises(ValidationError, funcuse.clean_fields)

    def test_functionalusecatetory_crud(self):
        # read
        fuc = FunctionalUseCategory.objects.filter(pk=1).first()
        self.assertEquals(fuc.title, "surfactant")
        self.assertEquals(fuc.description, "surfactant")

        # update
        fuc.title = "title updated"
        fuc.description = ""
        fuc.save()
        fuc = FunctionalUseCategory.objects.filter(pk=1).first()
        self.assertEquals(fuc.title, "title updated")
        self.assertEquals(fuc.description, "")

        # functionaluse associated
        fu = FunctionalUse.objects.filter(category=1).first()
        self.assertIsNotNone(fu)

        # delete
        fuc.delete()

        # funcationaluse associated should set to null now
        fu = FunctionalUse.objects.filter(category=1).first()
        self.assertIsNone(fu)

    def test_datagroupcurationworkflow(self):
        dg = DataGroup.objects.all().first()
        step = CurationStep.objects.all().first()
        DataGroupCurationWorkflow.objects.create(
            data_group=dg, curation_step=step, step_status="I"
        )
        dg = DataGroup.objects.filter(pk=dg.id).first()
        self.assertIsNotNone(dg.curation_steps)
        self.assertEqual(1, dg.curation_steps.count())
        step1 = dg.curation_steps.first()
        self.assertFalse(step1.data_group.workflow_complete)
        self.assertEqual(step1.curation_step.name, step.name)
        self.assertEqual(step1.curation_step.step_number, 1)
