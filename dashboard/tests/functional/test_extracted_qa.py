from django.test import TestCase, tag
from django.urls import resolve, reverse
from lxml import html

from dashboard.tests import factories
from dashboard.tests.loader import load_model_objects, fixtures_standard
from dashboard.models import (
    QAGroup,
    ExtractedText,
    ExtractedFunctionalUse,
    Script,
    DataGroup,
)


@tag("loader")
class ExtractedQaTest(TestCase):
    def setUp(self):
        self.objects = load_model_objects()
        self.client.login(username="Karyn", password="specialP@55word")

    def test_qa_group_creation(self):
        # test the assignment of a qa_group to extracted text objects
        pk = self.objects.extext.pk
        self.assertIsNone(self.objects.extext.qa_group)
        self.assertEqual(len(QAGroup.objects.all()), 0)
        pk = self.objects.extext.extraction_script.pk
        response = self.client.get(f"/qa/extractionscript/{pk}/")
        self.assertEqual(response.status_code, 200)
        qa_group = QAGroup.objects.get(
            extraction_script=self.objects.extext.extraction_script
        )
        ext = ExtractedText.objects.get(qa_group=qa_group)
        self.assertIsNotNone(ext.qa_group)
        response = self.client.get(f"/qa/extractedtext/{ext.pk}/")

    def test_qa_approval_redirect(self):
        # first need to create a QAGroup w/ this get request.
        self.client.get(f"/qa/extractionscript/{self.objects.exscript.pk}/")
        pk = self.objects.extext.pk
        response = self.client.post(f"/extractedtext/approve/{pk}/")
        self.assertEqual(
            response.url,
            f"/qa/extractionscript/?group_type={self.objects.gt.code}",
            (
                "User should be redirected to "
                "QA homepage after last extext is approved."
            ),
        )

    def test_qa_functional_use_chemicals(self):
        extext = factories.ExtractedTextFactory.create(
            data_document__data_group__group_type__code="FU"
        )
        factories.ExtractedFunctionalUseFactory.create_batch(99, extracted_text=extext)
        qs = extext.prep_functional_use_for_qa()
        self.assertEqual(99, qs.count())

        extext = factories.ExtractedTextFactory.create(
            data_document__data_group__group_type__code="FU"
        )
        factories.ExtractedFunctionalUseFactory.create_batch(100, extracted_text=extext)
        qs = extext.prep_functional_use_for_qa()
        self.assertEqual(100, qs.count())

        extext = factories.ExtractedTextFactory.create(
            data_document__data_group__group_type__code="FU"
        )
        factories.ExtractedFunctionalUseFactory.create_batch(105, extracted_text=extext)
        qs = extext.prep_functional_use_for_qa()
        self.assertEqual(100, qs.count())
        non_qa = ExtractedFunctionalUse.objects.filter(
            extracted_text=extext, qa_flag=False
        ).count()
        self.assertEqual(5, non_qa)


@tag("loader")
class ExtractedQaTestWithFixtures(TestCase):

    fixtures = fixtures_standard

    def setUp(self):
        self.client.login(username="Karyn", password="specialP@55word")

    def test_qa_manual_composition_index(self):
        """
        The yaml fixtures do not include any manually-extracted documents, 
        so this test uses some factories to generate some for each Composition
        data group
        """
        script = Script.objects.filter(title="Manual (dummy)", script_type="EX").first()
        dgs = DataGroup.objects.filter(group_type__code="CO")
        
        for dg in dgs:
            # add some manually-extracted records in proportion to
            # the count of records 
            doc_count = ExtractedText.objects.filter(
                data_document__data_group=dg
            ).count()
            factory_count = (doc_count // 2) + 1

            extext = factories.ExtractedTextFactory.create_batch(
                factory_count,
                data_document__data_group=dg,
                extraction_script=script,
                data_document__title=f"{dg.name} manually extracted doc",
            )

        print(ExtractedText.objects.filter(extraction_script=script).count())

        response = self.client.get(reverse("qa_manual_composition_index"))
        self.assertContains(response, "Walmart MSDS", count=6)


        

        


        



