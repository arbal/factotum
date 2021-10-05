import json
from dashboard.tests.loader import fixtures_standard
from django.contrib.auth.models import User
from dashboard import views
from django.test import TestCase, override_settings, RequestFactory
from dashboard.models import (
    RawChem,
    Script,
    ExtractedText,
    QAGroup,
    QANotes,
    ExtractedListPresence,
    ExtractedComposition,
    extracted_text,
)
from django.db.models import Count
from django.urls import reverse
from lxml import html


@override_settings(ALLOWED_HOSTS=["testserver"])
class TestQaPage(TestCase):
    fixtures = fixtures_standard

    def setUp(self):
        self.factory = RequestFactory()
        self.client.login(username="Karyn", password="specialP@55word")

    def test_qa_begin(self):
        """
        Check that starting the QA process flips the variable on the Script
        """
        self.assertFalse(
            Script.objects.get(pk=5).qa_begun,
            "The Script should have qa_begun of False at the beginning",
        )
        self.client.get("/qa/extractionscript/5/")
        self.assertTrue(
            Script.objects.get(pk=5).qa_begun, "qa_begun should now be true"
        )

    def test_new_qa_group_urls(self):
        # Script 5 has ExtractedText object
        pk = 5
        response = self.client.get(f"/qa/extractionscript/")
        self.assertIn("Composition - Ext. Script".encode(), response.content)
        self.assertIn(
            f"/qa/extractionscript/{pk}/'> Begin QA".encode(), response.content
        )
        response = self.client.get(f"/qa/extractionscript/{pk}/")
        et = ExtractedText.objects.filter(extraction_script=pk).first()
        self.assertIn(f"/qa/extractedtext/{et.pk}/".encode(), response.content)
        # After opening the URL, the following should be true:
        # One new QA group should be created
        group_count = QAGroup.objects.filter(script_id=pk).count()
        self.assertTrue(group_count == 1)
        # The ExtractionScript's qa_begun property should be set to True
        self.assertTrue(Script.objects.get(pk=pk).qa_begun)
        # The ExtractedText object should be assigned to the QA Group
        group_pk = QAGroup.objects.get(script_id=pk).pk
        et = ExtractedText.objects.filter(extraction_script=pk).first()
        self.assertTrue(et.qa_group_id == group_pk)
        # The link on the QA index page should now say "Continue QA"
        response = self.client.get(f"/qa/extractionscript/")
        self.assertIn(
            f"'/qa/extractionscript/{pk}/'> Continue QA".encode(), response.content
        )

    def test_doc_fields(self):
        """ The subtitle and note field should appear on the page """
        response = self.client.get(f"/qa/extractedtext/254780/")
        self.assertIn("Lorem ipsum dolor".encode(), response.content)
        self.assertIn("A list of chemicals with a subtitle".encode(), response.content)
        self.assertIn("Total Chemical Records".encode(), response.content)

    def test_qa_func_use_script(self):
        response = self.client.get("/qa/extractionscript/?group_type=FU")
        self.assertIn("/qa/extractionscript/15/'> Begin QA".encode(), response.content)
        self.assertIn("Functional use - Ext. Script".encode(), response.content)

    def test_qa_script_without_ext_text(self):
        # Begin from the QA index page
        response = self.client.get(f"/qa/extractionscript/")
        self.assertIn(f"/qa/extractionscript/5/'> Begin QA".encode(), response.content)
        # Script 9 has no ExtractedText objects
        pk = 9
        # a user will see no link on the QA index page, but it's still
        # possible to enter the URL
        response = self.client.get(f"/qa/extractionscript/{pk}/", follow=True)
        self.assertEqual(response.status_code, 200)

    def test_data_document_qa(self):
        # Open the QA page for a Composition ExtractedText record w/ no QA group
        # and is in a Script with < 100 documents
        scr = (
            Script.objects.annotate(num_ets=Count("extractedtext"))
            .filter(num_ets__lt=100)
            .filter(script_type="EX")
            .first()
        )
        pk = (
            ExtractedText.objects.filter(qa_group=None)
            .filter(extraction_script=scr)
            .filter(data_document__data_group__group_type__code="CO")
            .first()
            .pk
        )
        response = self.client.get(f"/qa/extractedtext/{pk}/")

        # After opening the QA link from the data document detail page, the
        # following should be true:
        # One new QA group should be created
        scr = ExtractedText.objects.get(pk=pk).extraction_script
        group_count = QAGroup.objects.filter(script=scr).count()
        self.assertTrue(group_count == 1)
        # The ExtractionScript's qa_begun property should be set to True
        self.assertTrue(scr.qa_begun)
        # The ExtractedText object should be assigned to the QA Group
        new_group = QAGroup.objects.get(script=scr)
        et = ExtractedText.objects.get(pk=pk)
        self.assertTrue(et.qa_group == new_group)
        # The link on the QA index page should now say "Continue QA"
        response = self.client.get(f"/qa/extractionscript/")
        self.assertContains(response, f"'/qa/extractionscript/{scr.pk}/'> Continue QA")

        # Open the QA page for an ExtractedText record that has no QA group and
        # is related to a script with over 100 documents
        scr = (
            Script.objects.annotate(num_ets=Count("extractedtext"))
            .filter(num_ets__gt=100)
            .first()
        )
        pk = ExtractedText.objects.filter(extraction_script=scr).first().pk
        response = self.client.get(f"/qa/extractedtext/{pk}/")
        scr = ExtractedText.objects.get(pk=pk).extraction_script
        # After opening the QA link from the data document detail page, the
        # following should be true:
        # One new QA group should be created
        new_group = QAGroup.objects.get(script=scr)

        # There should be a lot of ExtractedText records assigned to the QAGroup
        initial_qa_count = ExtractedText.objects.filter(qa_group=new_group).count()
        self.assertTrue(initial_qa_count > 100)

        # Select a document that shares a Script with the
        # QA Group created above BUT DOES NOT BELONG TO THE QA GROUP
        pk = (
            ExtractedText.objects.filter(extraction_script=scr)
            .filter(qa_group=None)
            .first()
        ).pk
        # Open its QA page via the /datdocument/qa path
        response = self.client.get(f"/qa/extractedtext/{pk}/")
        # Make sure that the number of documents in the QA Group has increased
        self.assertGreater(
            ExtractedText.objects.filter(qa_group=new_group).count(), initial_qa_count
        )

    def test_habitsandpractices(self):
        # Begin from the QA index page
        response = self.client.get(f"/habitsandpractices/54/")
        self.assertContains(response, "<b>Add New Habit and Practice</b>")

    def test_dd_link(self):
        # Open the Script page to create a QA Group
        response = self.client.get("/qa/extractedtext/5", follow=True)
        self.assertIn(b"/datadocument/5", response.content)

    def test_approval(self):
        # Open the Script page to create a QA Group
        self.client.get("/qa/extractionscript/5", follow=True)
        # Follow the first approval link
        self.client.get("/qa/extractedtext/7", follow=True)

    def test_hidden_fields(self):
        """ExtractionScript 15 includes a functional use data group with pk = 5.
        Its QA page should hide the composition fields """
        # Create the QA group by opening the Script's page
        response = self.client.get("/qa/extractionscript/15/", follow=True)
        # Open the DataGroup's first QA approval link
        response = self.client.get("/chemical/756/edit", follow=True)
        # A raw_cas field should be in the page
        self.assertIn(b'<input type="text" name="raw_cas"', response.content)
        # There should not be any unit_type field in the functional use QA display
        self.assertNotIn(b'<input type="text" name="unit_type"', response.content)
        # The values shown should match the functional use record, not the chemical record
        self.assertIn(b"Functional Use Chem1", response.content)

        # Go back to a different ExtractionScript
        response = self.client.get("/qa/extractionscript/5", follow=True)
        # Open the QA page for a non-FunctionalUse document
        response = self.client.get("/chemical/4/edit", follow=True)
        # This page should include a unit_type input form
        self.assertIn(b"unit_type", response.content)

    def test_cpcat_qa(self):
        # Begin from the Chemical Presence QA index page
        response = self.client.get(f"/qa/chemicalpresence/")
        self.assertIn(
            f"/qa/chemicalpresencegroup/49/'> View Chemical Presence Lists".encode(),
            response.content,
        )

        response = self.client.get(f"/qa/chemicalpresencegroup/49", follow=True)
        # The table should include the "Begin QA" link
        self.assertIn(
            f'/qa/extractedtext/254781/"> Begin QA'.encode(), response.content
        )

        elps = ExtractedListPresence.objects.filter(
            extracted_text__data_document_id=254781
        )
        self.assertEqual(elps.filter(qa_flag=True).count(), 0)
        response = self.client.get(f"/qa/extractedtext/254781/", follow=True)
        # Navigating to the extractedtext QA page should cause
        # the sampled child records to be flagged with qa_flag=True
        elps = ExtractedListPresence.objects.filter(
            extracted_text__data_document_id=254781
        )
        self.assertEqual(elps.filter(qa_flag=True).count(), 30)

        # The QA page should only show the flagged records
        elp_flagged = elps.filter(qa_flag=True).first()
        self.assertIn(elp_flagged.raw_cas.encode(), response.content)

        elp_not_flagged = elps.filter(qa_flag=False).first()
        self.assertNotContains(response, elp_not_flagged.raw_cas)

    def test_every_extractedtext_qa(self):
        # Attempt to open a QA page for every ExtractedText record
        for et in ExtractedText.objects.all():
            response = self.client.get(
                f"/qa/extractedtext/%s" % et.data_document_id, follow=True
            )
            if response.status_code != 200:
                pass

            self.assertEqual(response.status_code, 200)

    def test_cp_qa_no_extractedtext(self):
        # before remove all extractedtext of group 49
        response = self.client.get(f"/qa/chemicalpresence/")
        self.assertIn(f"/qa/chemicalpresencegroup/49/".encode(), response.content)
        # remove extractedtext of group 49
        ExtractedText.objects.filter(data_document__data_group__id=49).delete()
        # now this group should not show on page
        response = self.client.get(f"/qa/chemicalpresence/")
        self.assertNotIn(f"/qa/chemicalpresencegroup/49/".encode(), response.content)

    def test_cleaning_script_qa_begin(self):
        """
        For ExtractedComposition records:
        Opening the cleaning script detail page should start the the QA process 
        by creating a QA Group containing all the extracted documents
        """
        script_id = 16
        self.assertFalse(
            Script.objects.get(pk=script_id).qa_begun,
            "The Script should have qa_begun of False at the beginning",
        )
        ets = ExtractedText.objects.filter(cleaning_script_id=script_id)
        for et in ets:
            self.assertIsNone(et.cleaning_qa_group)
        self.client.get(reverse("qa_cleaning_script_detail", args=[16]))
        self.assertTrue(
            Script.objects.get(pk=script_id).qa_begun, "qa_begun should now be true"
        )

        qag = QAGroup.objects.filter(script_id=script_id).first()
        self.assertIsNotNone(qag, "Confirm the presence of the newly-created QA Group")
        ets = ExtractedText.objects.filter(cleaning_script_id=script_id)
        for et in ets:
            self.assertEqual(et.cleaning_qa_group_id, qag.pk)
        response = self.client.get(reverse("qa_composition_cleaning_index"))

        doctag = f'<td id="docs-{str(script_id)}">{str(ets.count())}</td>'.encode()
        self.assertIn(
            doctag,
            response.content,
            "the table should show the correct count of cleaned documents",
        )
        qadoc_count = ExtractedText.objects.filter(cleaning_qa_group_id=qag.pk).count()
        qatag = (
            f'<td id="qa-group-count-{str(script_id)}">{str(qadoc_count)}</td>'.encode()
        )
        self.assertIn(
            qatag,
            response.content,
            "the table should show the correct count of cleaned documents assigned to the Cleaning QA Group",
        )
        # proceed back to the script's QA detail page
        response = self.client.get(
            reverse("qa_cleaning_script_detail", args=[16])
        ).content.decode("utf8")
        # the chemical record count listed should match the number of ExtractedComposition records related to the document
        et_id = ExtractedText.objects.filter(cleaning_qa_group_id=qag.pk).first().pk
        chem_count_orm = ExtractedComposition.objects.filter(
            extracted_text_id=et_id
        ).count()
        chem_count_xpath = f'//*[@id="docrow-{et_id}"]/td[5]'
        response_html = html.fromstring(response)
        chem_count_table = int(response_html.xpath(chem_count_xpath)[0].text)
        self.assertEqual(chem_count_orm, chem_count_table)

    def test_qa_cleaned_composition_document_table(self):
        """
        Test the endpoint that populates the table of cleaned composition
        values agains the seed data
        """
        script_id = 16

        et_id = ExtractedText.objects.filter(cleaning_script_id=script_id).first().pk
        response = self.client.get(
            reverse("qa_cleaned_composition_detail_table", args=[et_id])
        ).content.decode("utf8")
        records = json.loads(response)
        tablechem = records["data"][0]
        dbchem = (
            RawChem.objects.filter(extracted_text_id=et_id)
            .filter(raw_chem_name=tablechem[0])
            .select_subclasses()
            .first()
        )
        self.assertEqual(tablechem[2], f"{float('%.4g' % dbchem.central_wf_analysis)}")

    def test_cleaning_script_qa_process(self):
        """
        Open the script page for cleaned ExtractedComposition records
        and go through the QA process
        """
        script_id = 16

        response = self.client.get(
            reverse("qa_cleaning_script_detail", args=[script_id])
        ).content.decode("utf8")
        qag = QAGroup.objects.filter(script_id=script_id).first()
        et = ExtractedText.objects.filter(cleaning_qa_group_id=qag.pk).first()
        et_id = et.pk
        doc_link_xpath = f'//*[@id="qa-link-{et_id}"]'

        response_html = html.fromstring(response)
        # find the document detail link
        doc_detail_button = response_html.get_element_by_id(f"qa-link-{et_id}")
        doc_detail_text = response_html.xpath(doc_link_xpath)[0].text
        self.assertHTMLEqual("Not reviewed", doc_detail_text)

        doc_qa_url = doc_detail_button.get("href")
        response = self.client.get(doc_qa_url).content.decode("utf8")
        detail_html = html.fromstring(response)
        # the table of extracted composition values has not loaded yet,
        # so trust the other test for that part

        # Check the Exit button's link
        exit_button = detail_html.get_element_by_id("exit")
        exit_url = exit_button.get("href")
        self.assertEqual(
            reverse("qa_cleaning_script_detail", args=[script_id]), exit_url
        )

        # The Skip button should be disabled, since this is the only
        # document in the QA group
        skip_button = detail_html.get_element_by_id("skip")
        skip_status = skip_button.get("aria-disabled")
        self.assertTrue(skip_status)

        # The "Reject" button is part of a form
        reject_form = detail_html.get_element_by_id("reject-form")
        reject_path = reject_form.get("action")
        response = self.client.post(reject_path, follow=True)
        # Rejecting the document should redirect the user to the cleaning script QA index
        self.assertEqual(
            response.status_code,
            200,
            "User should be redirected to the QA script's detail page",
        )
        self.assertRedirects(
            response, reverse("qa_cleaning_script_detail", args=[script_id])
        )
        message = list(response.context.get("messages"))[0]
        rejection_text = f"The cleaned composition data for {et.data_document.title} has been rejected."
        self.assertEqual(rejection_text, message.message)
        et = ExtractedText.objects.get(pk=et_id)
        self.assertEqual(et.cleaning_qa_checked, False)

        # Approve the same document
        approve_form = detail_html.get_element_by_id("approve-form")
        approve_path = approve_form.get("action")
        response = self.client.post(approve_path, follow=True)
        # Rejecting the document should redirect the user to the cleaning script QA index
        self.assertEqual(
            response.status_code,
            200,
            "User should be redirected to the QA script's detail page",
        )
        self.assertRedirects(
            response, reverse("qa_cleaning_script_detail", args=[script_id])
        )
        message = list(response.context.get("messages"))[0]
        approval_text = f"The cleaned composition data for {et.data_document.title} has been approved!"
        self.assertEqual(approval_text, message.message)
        et = ExtractedText.objects.get(pk=et_id)
        self.assertEqual(et.cleaning_qa_checked, True)
