import re
import time

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait

from dashboard.models import (
    DataDocument,
    ExtractedText,
    RawChem,
    DataGroup,
    Script,
    CurationStep,
)
from dashboard.tests.loader import fixtures_standard, load_browser


def log_karyn_in(object):
    """
    Log user in for further testing.
    """
    object.browser.get(object.live_server_url + "/login/")
    body = object.browser.find_element_by_tag_name("body")
    object.assertIn("Please sign in", body.text)
    username_input = object.browser.find_element_by_name("username")
    username_input.send_keys("Karyn")
    password_input = object.browser.find_element_by_name("password")
    password_input.send_keys("specialP@55word")
    object.browser.find_element_by_class_name("btn").click()


class TestEditsWithSeedData(StaticLiveServerTestCase):
    fixtures = fixtures_standard

    def setUp(self):
        self.browser = load_browser()
        log_karyn_in(self)

    def tearDown(self):
        self.browser.quit()

    def test_break_curation(self):
        """
        Changing the raw_cas or raw_chemname on a RawChem record with a related DssToxLookup should cause
        the relationship to be deleted.
        The RID should also be removed.
        """
        # currently uses a single data document
        ets_with_curation = ExtractedText.objects.filter(
            rawchem__dsstox__isnull=False
        ).filter(pk=245401)
        for et in ets_with_curation:
            doc_qa_link = f"/qa/extractedtext/{et.data_document_id}/"
            self.browser.get(self.live_server_url + doc_qa_link)
            rc_id = et.rawchem.last().id
            btn_edit = self.browser.find_element_by_id(f"chemical-update-{rc_id}")
            btn_edit.click()
            save_button = wait.until(
                ec.element_to_be_clickable((By.XPATH, "//*[@id='saveChem']"))
            )
            self.browser.find_element_by_id("id_raw_cas").send_keys("changed cas")
            save_button.click()
            wait.until(
                ec.element_to_be_clickable((By.XPATH, "//*[@id='approve']"))
            )
            time.sleep(1)
            rc = RawChem.objects.get(pk=rc_id)  # reload the rawchem record
            print(rc.dsstox)
            self.assertEqual(
                None,
                rc.dsstox,
                "The same rawchem record should now have nothing in its dsstox link",
            )
            self.assertEqual(
                "", rc.rid, "The same rawchem record should now have no RID"
            )

    def test_new_chem(self):
        """
        Adding a new ExtractedComposition without a unit type should return a validation error
        if the raw_..._comp fields are not all empty
        """
        # currently "loops" over just a single data document. Other cases can be added
        ets_with_curation = ExtractedText.objects.filter(
            rawchem__dsstox__isnull=False
        ).filter(pk=245401)
        for et in ets_with_curation:
            doc_qa_link = f"/qa/extractedtext/{et.data_document_id}/"
            self.browser.get(self.live_server_url + doc_qa_link)
            self.browser.find_element_by_id(f"chemical-add-btn").click()
            # wait for the Save button to be clickable
            wait = WebDriverWait(self.browser, 10)
            save_button = wait.until(
                ec.element_to_be_clickable((By.XPATH, "//*[@id='saveChem']"))
            )
            # edit the Raw CAS field
            raw_cas_input = self.browser.find_element_by_xpath(
                '//*[@id="id_raw_cas"]'
            )
            raw_cas_input.send_keys("test raw cas")

            raw_min_comp_input = self.browser.find_element_by_xpath(
                '//*[@id="id_raw_min_comp"]'
            )
            raw_min_comp_input.send_keys("1")

            raw_max_comp_input = self.browser.find_element_by_xpath(
                '//*[@id="id_raw_max_comp"]'
            )
            raw_min_comp_input.send_keys("1")

            save_button.send_keys("\n")

            # Check for the error message after clicking Save
            wait.until(ec.visibility_of(self.browser.find_element_by_id("chem-card-")))
            self.browser.find_element_by_id("chem-card-").click()
            parent_div = self.browser.find_element_by_xpath(
                '//*[@id="id_rawchem-1-raw_cas"]/parent::*'
            )
            card_div = parent_div.find_element_by_xpath("../..")
            self.assertTrue(
                "There must be a unit type if a composition value is provided."
                in card_div.get_attribute("innerHTML")
            )

            # Try editing a new record correctly
            self.browser.get(self.live_server_url + doc_qa_link)

            # wait for the Save button to be clickable
            wait = WebDriverWait(self.browser, 10)
            save_button = wait.until(
                ec.element_to_be_clickable((By.XPATH, "//*[@id='saveChem']"))
            )
            raw_cas_input = self.browser.find_element_by_xpath(
                '//*[@id="id_raw_cas"]'
            )
            raw_cas_input.send_keys("test raw cas")
            raw_min_comp_input = self.browser.find_element_by_xpath(
                '//*[@id="id_min_comp"]'
            )
            raw_min_comp_input.send_keys("1")
            # This time, set a unit_type
            unit_type_select = Select(
                self.browser.find_element_by_xpath('//*[@id="id_unit_type"]')
            )
            unit_type_select.select_by_index(1)

            save_button.send_keys("\n")
            # Check for the absence of an error message after clicking Save
            parent_div = self.browser.find_element_by_xpath(
                '//*[@id="id_raw_cas"]/parent::*'
            )
            card_div = parent_div.find_element_by_xpath("../..")
            self.assertFalse(
                "There must be a unit type if a composition value is provided."
                in card_div.get_attribute("innerHTML")
            )

    def test_redirects(self):
        """
        Editing the data document type should return the user to the page on which the edits were made
        """
        for doc_id in [7]:
            # QA Page
            doc_qa_link = f"/qa/extractedtext/%s/" % doc_id
            self.browser.get(self.live_server_url + doc_qa_link)
            doc_type_select = Select(
                self.browser.find_element_by_xpath('//*[@id="id_document_type"]')
            )
            doc_type_select.first_selected_option
            doc_type_select.select_by_visible_text("ingredient disclosure")
            self.assertIn(doc_qa_link, self.browser.current_url)

    def test_qa_approval(self):
        """
        Test the QA process in the browser
        1. Open the QA page for an ExtractedText record
        2. Edit one of the child records
        3. Attempt to approve the document without a QA note
        4. Add a note
        5. Approve
        """
        # Start off by testing the "Percent QA Checked" stat shown in the table
        # on the QA index page
        self.browser.get(self.live_server_url + "/qa/chemicalpresence/")
        td_pct_checked = self.browser.find_element_by_xpath(
            '//*[@id="chemical_presence_table"]/tbody/tr[2]/td[4]'
        )
        self.assertEqual(
            td_pct_checked.text,
            "0%",
            "Percent QA Checked for the second row on the Chemical Presence QA index should be zero",
        )
        self.browser.implicitly_wait(10)
        for doc_id in [
            7,  # Composition
            5,  # Functional Use
            254781,  # Chemical Presence List
            354783,  # HHE Report
        ]:
            # QA Page
            qa_url = self.live_server_url + f"/qa/extractedtext/{doc_id}/"
            self.browser.get(qa_url)
            # Activate the edit mode
            wait = WebDriverWait(self.browser, 10)
            # For CP groups only 30 raw chems (set in ExtractedCPCat.prep_cp_for_qa()) are
            # designated for review.  Find the first and edit that.
            btn_accordion = wait.until(
                ec.element_to_be_clickable(
                    (By.XPATH, f"//*[starts-with(@id, 'chem-')]")
                )
            )
            btn_accordion.click()
            # Find chemical card, not chem-card-None (i.e. "Add new chemical")
            chem_cards = self.browser.find_elements_by_xpath(
                "//*[starts-with(@id, 'chem-card-')]"
            )
            regex = re.compile("chem-card-\d+")
            chem_card = next(c for c in chem_cards if regex.match(c.get_property("id")))
            chem_card.click()

            # Wait for the field to be editable

            raw_chem_name_field = wait.until(
                ec.element_to_be_clickable(
                    (By.XPATH, "//*[@id='id_rawchem-0-raw_chem_name']")
                )
            )

            old_raw_chem_name = raw_chem_name_field.get_attribute("value")

            # Get the detailed child record's ID
            rawchem_id_field = self.browser.find_element_by_xpath(
                '//*[@id="id_rawchem-0-rawchem_ptr"]'
            )
            rawchem_id = rawchem_id_field.get_attribute("value")

            # Modify the first raw_chem_name field's value and save changes
            raw_chem_name_field.send_keys(" edited")
            self.browser.find_element_by_xpath('//*[@id="save"]').click()

            # Confirm the changes in the ORM
            rc = RawChem.objects.get(pk=rawchem_id)
            self.assertEqual(
                rc.raw_chem_name,
                f"%s edited" % old_raw_chem_name,
                "The raw_chem_name field should have changed",
            )

            et = ExtractedText.objects.get(pk=doc_id)
            self.assertTrue(et.qa_edited, "The qa_edited attribute should be True")

            # Click Approve without any notes and confirm that approval fails
            self.browser.find_element_by_xpath('//*[@id="approve"]').send_keys("\n")

            # The page should include an error message like this one:
            """
                <div class="alert alert-danger alert-dismissible" role="alert">
                <button type="button" class="close" data-dismiss="alert" aria-label="Close">
                    <span aria-hidden="true">×</span>
                </button>
                The extracted text
                could not be approved. Make sure that if the records have been edited,
                the QA Notes have been populated.
                </div>
            """
            message_element = self.browser.find_element_by_xpath(
                "/html/body/div[1]/div[1]"
            )
            self.assertIn("alert", message_element.get_attribute("role"))
            et.refresh_from_db()
            self.assertFalse(et.qa_checked, "The qa_checked attribute should be False")

            qa_notes_field = self.browser.find_element_by_xpath(
                '//*[@id="qa-notes-textarea"]'
            )
            # Add the mandatory QA note
            qa_notes_field.send_keys(f"Some QA Notes for document {doc_id}")
            # Save the notes
            btn_save_notes = self.browser.find_element_by_xpath(
                '//*[@id="btn-save-notes"]'
            )
            btn_save_notes.click()
            # Click "Approve" again
            self.browser.find_element_by_xpath('//*[@id="approve"]').click()
            et.refresh_from_db()
            self.assertTrue(et.qa_checked, "The qa_checked attribute should be True")

            # Go to the extraction script's summary page
            scr_id = et.extraction_script_id
            qa_summary_url = (
                self.live_server_url + f"/qa/compextractionscript/{scr_id}/summary"
            )
            self.browser.get(qa_summary_url)

            # This ajax call seems to be a little (incredibly) finicky.  Upping the wait to ensure it finishes
            wait = WebDriverWait(self.browser, 60)
            wait.until(
                ec.text_to_be_present_in_element(
                    (By.XPATH, '//table[@id="document-table"]/tbody'),
                    et.data_document.title,
                )
            )
            doc_table = self.browser.find_element_by_xpath(
                '//table[@id="document-table"]/tbody'
            )
            self.assertIn(
                et.data_document.title,
                doc_table.text,
                "The Document table element should contain Documents",
            )

        # Return to the index page and confirm that the "Percent QA Checked"
        # stat has gone up
        self.browser.get(self.live_server_url + "/qa/chemicalpresence/")
        td_pct_checked = self.browser.find_element_by_xpath(
            '//*[@id="chemical_presence_table"]/tbody/tr[2]/td[4]'
        )
        self.assertEqual(
            td_pct_checked.text,
            "33%",
            "Percent QA Checked for the second row on the Chemical Presence QA index should be 33%",
        )

    def test_datadoc_add_extracted(self):
        """
        Test that when a datadocument has no ExtractedText,
        the user can add one in the browser
        1.
        """

        for doc_id in [155324]:  # CO record with no ExtractedText
            # QA Page
            dd_url = self.live_server_url + f"/datadocument/{doc_id}/"
            self.browser.get(dd_url)
            # Activate the edit mode
            wait = WebDriverWait(self.browser, 10)
            add_button = wait.until(
                ec.element_to_be_clickable(
                    (By.XPATH, '//*[@id="btn-add-or-edit-extracted-text"]')
                )
            )
            add_button.click()

            # Verify that the modal window appears by finding the Cancel button
            # The modal window does not immediately appear, so the browser
            # should wait for the button to be clickable
            cancel_button = wait.until(
                ec.element_to_be_clickable(
                    (By.XPATH, "//*[@id='extracted-text-modal-cancel']")
                )
            )
            self.assertEqual(
                "Cancel", cancel_button.text, "The Cancel button should say Cancel"
            )
            cancel_button.click()
            # Verify that no ExtractedText record was created
            self.assertEqual(
                0,
                ExtractedText.objects.filter(data_document_id=doc_id).count(),
                "the count of ExtractedText records related to the \
                data document should be zero",
            )

            # Wait for the modal div to disappear
            wait.until(ec.invisibility_of_element((By.XPATH, '//*[@id="extextModal"]')))
            # Click the Add button again to reopen the editor
            add_button = self.browser.find_element_by_xpath(
                '//*[@id="btn-add-or-edit-extracted-text"]'
            )
            add_button.click()

            # Once again, check that the controls on the modal form are clickable
            # before trying to interact with them
            wait.until(
                ec.element_to_be_clickable(
                    (By.XPATH, "//*[@id='extracted-text-modal-cancel']")
                )
            )
            self.browser.find_element_by_xpath("//input[@id='id_prod_name']").send_keys(
                "Fake Product"
            )
            self.browser.find_element_by_id("extracted-text-modal-save").click()
            self.browser.refresh()

            # Confirm the presence of the new ExtractedText record
            et = ExtractedText.objects.get(data_document_id=doc_id)
            self.assertEqual(
                "Fake Product",
                et.prod_name,
                "The prod_name of the new object should match what was entered",
            )

    def test_delete_dd_from_dg(self):
        """
        The seed data includes an unmatched data document that
        can be deleted from the data group detail page.
        Confirm that the delete button works.
        """
        dd = DataDocument.objects.get(id=354788)
        dg_id = dd.data_group.id
        dg_url = self.live_server_url + f"/datagroup/{dg_id}/"
        self.browser.get(dg_url)
        # Wait for the trash can to be clickable
        wait = WebDriverWait(self.browser, 10)
        trash_can = wait.until(
            ec.element_to_be_clickable(
                (By.XPATH, "//*[@id='docs']/tbody/tr[3]/td[2]/div/a")
            )
        )
        # The URL is correct
        self.assertIn("/datadocument/delete/354788/", trash_can.get_attribute("href"))
        trash_can.click()
        # The browser redirects to the confirmation page
        self.assertIn("/datadocument/delete/354788/", self.browser.current_url)

        confirm_button = self.browser.find_element_by_xpath(
            "/html/body/div[1]/form/input[2]"
        )
        confirm_button.click()
        # It needs a pause to avoid ConnectionResetError
        time.sleep(3)
        # Clicking the confirm button redirects to the data group page
        self.assertIn(dg_url, self.browser.current_url)
        # and removes the record
        self.assertFalse(DataDocument.objects.filter(id=354788).exists())

    def test_extracted_datatable_filter(self):
        self.browser.get(self.live_server_url + "/datagroup/18/")
        wait = WebDriverWait(self.browser, 10)
        trash_can = wait.until(
            ec.element_to_be_clickable((By.XPATH, "//*[@id='footer-options']"))
        )
        banner = wait.until(
            ec.element_to_be_clickable((By.CLASS_NAME, "dataTables_info"))
        )
        wait.until(
            ec.text_to_be_present_in_element(
                (By.CLASS_NAME, "dataTables_info"), "Showing 1 to 4 of 4 entries"
            )
        )
        self.assertEqual(banner.text, "Showing 1 to 4 of 4 entries")
        not_extracted = trash_can.find_element_by_name("Not_extracted")
        not_extracted.click()
        self.assertEqual(
            banner.text, "Showing 1 to 1 of 1 entries (filtered from 4 total entries)"
        )
        extracted = trash_can.find_element_by_name("Extracted")
        extracted.click()
        self.assertEqual(
            banner.text, "Showing 1 to 3 of 3 entries (filtered from 4 total entries)"
        )

    def test_chemical_presence_summary_page(self):
        doc_id = 254781
        extractedtext = ExtractedText.objects.get(pk=doc_id)
        datagroup_id = extractedtext.data_document.data_group.id
        qa_notes = "test notes"

        # QA Page
        qa_url = self.live_server_url + f"/qa/extractedtext/{doc_id}/"
        self.browser.get(qa_url)
        wait = WebDriverWait(self.browser, 10)

        # add QA note
        self.browser.find_element_by_xpath('//*[@id="qa-notes-textarea"]').send_keys(
            qa_notes
        )
        self.browser.find_element_by_xpath('//*[@id="btn-save-notes"]').click()

        # approve it
        self.browser.find_element_by_xpath('//*[@id="approve"]').send_keys("\n")

        # verify the summary page
        self.browser.get(
            self.live_server_url + f"/qa/chemicalpresencegroup/{datagroup_id}/summary"
        )
        wait.until(ec.visibility_of(self.browser.find_element_by_id("document-table")))
        self.assertEqual("3", self.browser.find_element_by_id("document_count").text)
        self.assertEqual("1", self.browser.find_element_by_id("qa_complete_count").text)
        self.assertEqual(
            "2", self.browser.find_element_by_id("qa_incomplete_count").text
        )
        time.sleep(2)

        self.assertEqual(
            extractedtext.data_document.data_group.name,
            self.browser.find_element_by_xpath(
                '//table[@id="document-table"]/tbody/tr[1]/td[1]'
            ).text,
        )
        self.assertEqual(
            extractedtext.data_document.title,
            self.browser.find_element_by_xpath(
                '//table[@id="document-table"]/tbody/tr[1]/td[2]'
            ).text,
        )
        self.assertEqual(
            qa_notes,
            self.browser.find_element_by_xpath(
                '//table[@id="document-table"]/tbody/tr[1]/td[3]'
            ).text,
        )
        self.assertEqual(
            "50",
            self.browser.find_element_by_xpath(
                '//table[@id="document-table"]/tbody/tr[1]/td[4]'
            ).text,
        )
        self.assertIn(
            "Last updated",
            self.browser.find_element_by_xpath(
                '//table[@id="document-table"]/tbody/tr[1]/td[5]'
            ).text,
        )

    def test_edit_qa_summary_note(self):
        wait = WebDriverWait(self.browser, 10)
        # edit script summary note
        script = Script.objects.first()
        self.browser.get(
            self.live_server_url + f"/qa/compextractionscript/{script.pk}/summary"
        )
        save_button = wait.until(
            ec.element_to_be_clickable((By.XPATH, "//*[@id='btn-save-notes']"))
        )
        note = "this is a test note"
        self.browser.find_element_by_id("qa-summary-note-textarea").send_keys(note)
        save_button.click()
        time.sleep(1)
        script = Script.objects.get(pk=script.pk)
        self.assertEqual(note, script.qa_summary_note)

        # edit cp summary note
        datagroup = DataGroup.objects.filter(group_type__code="CP").first()
        self.browser.get(
            self.live_server_url + f"/qa/chemicalpresencegroup/{datagroup.pk}/summary"
        )
        save_button = wait.until(
            ec.element_to_be_clickable((By.XPATH, "//*[@id='btn-save-notes']"))
        )
        note = "this is a another test note"
        self.browser.find_element_by_id("qa-summary-note-textarea").send_keys(note)
        save_button.click()
        time.sleep(1)
        datagroup = DataGroup.objects.get(pk=datagroup.pk)
        self.assertEqual(note, datagroup.qa_summary_note)

    def test_duplicate_chemicals_page(self):
        duplicate_chemicals_url = self.live_server_url + "/duplicate_chemicals/"
        self.browser.get(duplicate_chemicals_url)
        time.sleep(1)
        document_cell = self.browser.find_element_by_xpath(
            '//*[@id="duplicate-chemicals"]/tbody/tr[1]/td[1]'
        )
        sid_cell = self.browser.find_element_by_xpath(
            '//*[@id="duplicate-chemicals"]/tbody/tr[1]/td[2]'
        )
        self.assertIn("Sun_INDS_89", document_cell.text)
        self.assertIn("DTXSID9022528", sid_cell.text)

    def test_data_group_tracking(self):
        url = self.live_server_url + "/data_group_tracking/"
        datagroup = DataGroup.objects.order_by("name").first()
        edit_url = self.live_server_url + f"/data_group_tracking/edit/{datagroup.id}/"
        curation_steps = CurationStep.objects.all()

        # test table
        self.browser.get(url)
        time.sleep(1)
        datasource_cell = self.browser.find_element_by_xpath(
            '//*[@id="datagroups"]/tbody/tr[1]/td[1]'
        )
        self.assertIn(datagroup.data_source.title, datasource_cell.text)
        datagroup_cell = self.browser.find_element_by_xpath(
            '//*[@id="datagroups"]/tbody/tr[1]/td[2]'
        )
        self.assertIn(datagroup.name, datagroup_cell.text)
        type_cell = self.browser.find_element_by_xpath(
            '//*[@id="datagroups"]/tbody/tr[1]/td[3]'
        )
        self.assertIn(datagroup.group_type.title, type_cell.text)
        col_index = 5
        for step in curation_steps:
            step_header = self.browser.find_element_by_xpath(
                f"//*[@id='datagroups']/thead/tr/th[{col_index}]"
            )
            self.assertEqual(step.name, step_header.text)
            step_cell = self.browser.find_element_by_xpath(
                f"//*[@id='datagroups']/tbody/tr[1]/td[{col_index}]"
            )
            self.assertEqual("Incomplete", step_cell.text)
            col_index = col_index + 1
        workflow_cell = self.browser.find_element_by_xpath(
            f"//*[@id='datagroups']/tbody/tr[1]/td[{col_index}]"
        )
        self.assertEqual("No", workflow_cell.text)

        # test edit page
        self.browser.get(edit_url)
        time.sleep(1)
        for step in curation_steps:
            step_field = Select(
                self.browser.find_element_by_id("id_step_" + str(step.id))
            )
            self.assertEqual("Incomplete", step_field.first_selected_option.text)
            step_field.select_by_index(2)
        workflow_field = self.browser.find_element_by_id("id_workflow_complete")
        self.assertFalse(workflow_field.get_attribute("checked"))
        workflow_field.click()
        self.browser.find_element_by_xpath("//button[@type='submit']").click()
        time.sleep(1)
        # verify data saved
        datagroup = DataGroup.objects.filter(pk=datagroup.id).first()
        self.assertTrue(datagroup.workflow_complete)
        self.assertEqual(curation_steps.count(), datagroup.curation_steps.count())
        for step in datagroup.curation_steps.all():
            self.assertEqual("N", step.step_status)
        # load page again, should set new values
        self.browser.get(edit_url)
        time.sleep(1)
        for step in curation_steps:
            step_field = Select(
                self.browser.find_element_by_id("id_step_" + str(step.id))
            )
            self.assertEqual("N/A", step_field.first_selected_option.text)
        workflow_field = self.browser.find_element_by_id("id_workflow_complete")
        self.assertTrue(workflow_field.get_attribute("checked"))
