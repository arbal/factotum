from dashboard.tests.loader import fixtures_standard, load_browser
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from dashboard.models import ExtractedText, Script
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select


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

    def test_document_attribute_edit(self):
        """The user should be able to open the document-editing screen from the 
        QA page, and the Submit and Cancel buttons should return the user to the
        original QA page.
        Fields include:
            data document title
            subtitle
            raw category
            URL
            Note
            data document type
        """
        # Habits & Practices example
        qa_url = self.live_server_url + f"/qa/extractedtext/53/"
        self.browser.get(qa_url)
        btn_edit = self.browser.find_element_by_id("edit_document")
        btn_edit.click()
        self.assertEqual(
            self.browser.current_url, self.live_server_url + f"/datadocument/edit/53/"
        )
        # Canceling
        btn_cancel = self.browser.find_element_by_name("cancel")
        btn_cancel.click()
        # the browser should return to the QA page
        self.assertEqual(self.browser.current_url, qa_url)

        # Editing
        btn_edit = self.browser.find_element_by_id("edit_document")
        btn_edit.click()

        subtitle_input = self.browser.find_element_by_id("id_subtitle")
        subtitle_input.send_keys("New subtitle")

        document_type_select = Select(
            self.browser.find_element_by_xpath('//*[@id="id_document_type"]')
        )
        document_type_select.select_by_visible_text("journal article")

        btn_submit = self.browser.find_element_by_name("submit")
        btn_submit.click()
        # the browser should return to the QA page
        self.assertEqual(self.browser.current_url, qa_url)
        wait = WebDriverWait(self.browser, 10)
        subtitle_input = wait.until(
            EC.visibility_of(self.browser.find_element_by_id("subtitle"))
        )
        self.assertEqual(subtitle_input.text, "New subtitle")

        document_type_select = Select(
            self.browser.find_element_by_id("id_document_type")
        )
        self.assertEqual(
            document_type_select.first_selected_option.text, "journal article"
        )

    def test_extracted_text_delete_confirmation(self):
        extraction_script = Script.objects.get(pk=5)
        self.assertEqual(
            2, ExtractedText.objects.filter(extraction_script=extraction_script).count()
        )

        qa_url = self.live_server_url + f"/extractionscripts/delete"
        self.browser.get(qa_url)

        self.assertEqual(
            2, ExtractedText.objects.filter(extraction_script=extraction_script).count()
        )
        with self.assertRaises(NoSuchElementException):
            self.browser.find_element_by_class_name("popover")

        et_delete_button = self.browser.find_element_by_id("et-delete-button-5")
        et_delete_button.send_keys("\n")

        wait = WebDriverWait(self.browser, 10)
        popover_div = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "popover")))
        # popover_div = self.browser.find_element_by_class_name("popover")
        self.assertIn(
            "This action will delete 2 extracted text records.", popover_div.text
        )

        confirm_button = popover_div.find_element_by_class_name("btn-primary")
        confirm_button.send_keys("\n")

        with self.assertRaises(NoSuchElementException):
            self.browser.find_element_by_id("et-delete-button-5")

        extraction_script.refresh_from_db()
        self.assertEqual(
            0, ExtractedText.objects.filter(extraction_script=extraction_script).count()
        )
        self.assertEqual(False, extraction_script.qa_begun)

    def test_skip_button(self):
        # A Composition page should include a Skip button
        qa_url = self.live_server_url + f"/qa/extractedtext/121698/"
        self.browser.get(qa_url)
        btn_skip = self.browser.find_element_by_name("skip")
        self.assertEqual(btn_skip.text, "Skip")

        # A Chemical Presence page should not
        qa_url = self.live_server_url + f"/qa/extractedtext/254780/"
        self.browser.get(qa_url)
        with self.assertRaises(NoSuchElementException):
            self.browser.find_element_by_name("skip")

    def test_chemical_auditlog(self):
        extracted_text = ExtractedText.objects.filter(pk__in=[156051, 354786])
        for et in extracted_text:
            list_url = self.live_server_url + f"/qa/extractedtext/{et.pk}/"
            self.browser.get(list_url)
            chem = et.rawchem.last()
            self.browser.find_element_by_xpath(
                f'//*[@id="chem-card-{chem.pk}"]'
            ).click()

            wait = WebDriverWait(self.browser, 10)
            audit_link = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, f"//*[@id='chemical-audit-log-{chem.pk}']")
                )
            )
            self.assertIn("Last updated", audit_link.text)
            audit_link.click()

            datatable = wait.until(
                EC.visibility_of_element_located((By.XPATH, "//*[@id='audit-log']"))
            )
            self.assertIn("report_funcuse", datatable.text)
