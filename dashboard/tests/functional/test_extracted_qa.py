import json

from django.test import TestCase, tag
from django.urls import reverse

from dashboard.tests import factories
from dashboard.tests.loader import load_model_objects, fixtures_standard
from dashboard.models import (
    QAGroup,
    ExtractedText,
    ExtractedFunctionalUse,
    Script,
    DataGroup,
    QANotes,
    data_document,
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


class ExtractedQaTestWithFixtures(TestCase):

    fixtures = fixtures_standard

    def setUp(self):
        self.client.login(username="Karyn", password="specialP@55word")

    def test_qa_manual_composition(self):
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

            factories.ExtractedTextFactory.create_batch(
                factory_count,
                data_document__data_group=dg,
                extraction_script=script,
                data_document__title=f"{dg.name} manually extracted doc",
            )

        response = self.client.get(reverse("qa_manual_composition_index"))
        self.assertContains(response, "Walmart MSDS", count=18)

        # test datagroup
        extext = ExtractedText.objects.filter(extraction_script=script).first()
        data_group = extext.data_document.data_group
        response = self.client.get(
            reverse("qa_manual_composition_script", kwargs={"pk": data_group.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, f"Manual Composition Documents for Data Group: {data_group.name}"
        )

        # test summary count
        # add qa note and approve it
        notes = "test qa notes"
        QANotes.objects.create(extracted_text=extext, qa_notes=notes)
        extext.qa_checked = True
        extext.save()
        total_count = ExtractedText.objects.filter(
            extraction_script=script, data_document__data_group=data_group
        ).count()
        response = self.client.get(
            reverse("qa_manual_composition_summary", kwargs={"pk": data_group.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'id="document_count">{total_count}')
        self.assertContains(response, 'id="qa_complete_count">1')
        self.assertContains(response, 'id="qa_notes">1')
        # test summary table
        response = self.client.get(
            reverse("qa_manual_composition_summary_table", kwargs={"pk": data_group.pk})
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["recordsTotal"], 1)
        row = data["data"][0]
        self.assertIn(data_group.name, row[0])
        self.assertIn(extext.data_document.title, row[1])
        self.assertEquals(notes, row[2])

        # pick a new ExtractedText to work with
        extext = ExtractedText.objects.filter(
            data_document__data_group=data_group, extraction_script=script
        )[5]
        docid = extext.pk
        # Open a document's QA page
        response = self.client.get(reverse("extracted_text_qa", kwargs={"pk": docid}))

        # The breadcrumb navigation should direct to the manualcomposition path
        self.assertContains(response, f"/qa/manualcomposition/{data_group.id}/")

        # The count of remaining documents should reflect the data group's manual
        # documents, not the QAGroup for the manual extraction script.
        a = extext.get_approved_doc_count()
        r = extext.get_qa_queryset().filter(qa_checked=False).count()
        stats = "%s document(s) approved, %s documents remaining" % (a, r)

        self.assertContains(response, stats)

        # Approval should redirect to the next manually-extracted composition
        # record in the data group
        nextid = extext.next_extracted_text_in_qa_group()
        response = self.client.post(f"/extractedtext/approve/{extext.pk}/", follow=True)
        self.assertRedirects(response, f"/qa/extractedtext/{nextid}/")

        # Confirm that the approval was applied
        self.assertTrue(ExtractedText.objects.get(pk=docid).qa_checked)

        # the page is showing a new document now
        extext = ExtractedText.objects.get(pk=nextid)
        # Check that the title matches
        self.assertContains(response, f"Data Document: {extext.data_document.title}")

        # On the post-approval page:
        # the approved/remaining counts should be incremented or decremented
        # accordingly
        a = a + 1
        r = r - 1
        stats = "%s document(s) approved, %s documents remaining" % (a, r)
        self.assertContains(response, stats)

        # The "exit" button should return the user to the QA summary
        # page for the data group, not the script.

        # update the nextid
        nextid = extext.next_extracted_text_in_qa_group()
        skip_html = f'href="/qa/extractedtext/{nextid}/"'
        # The "skip" button should return the user to the QA summary
        # page for the data group, not the script.
        self.assertContains(response, skip_html)


