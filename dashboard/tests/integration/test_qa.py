from celery_djangotest.integration import TransactionTestCase
from celery_usertask.models import UserTaskLog
from dashboard.tests.loader import fixtures_standard, load_browser
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from dashboard.models import ExtractedText, Script
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.keys import Keys
from django.urls import reverse


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


class element_has_css_class(object):
    """An expectation for checking that an element has a particular css class.

    locator - used to find the element
    returns the WebElement once it has the particular css class
    """

    def __init__(self, locator, css_class):
        self.locator = locator
        self.css_class = css_class

    def __call__(self, driver):
        element = driver.find_element(*self.locator)  # Finding the referenced element
        if self.css_class in element.get_attribute("class"):
            return element
        else:
            return False


class TestEditsWithSeedData(StaticLiveServerTestCase, TransactionTestCase):
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

        qa_url = self.live_server_url + f"/extractionscripts/delete/"
        delete_detail_url = self.live_server_url + f"/extractedtext/delete/5/"
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

        # should direct to delete detail page
        self.assertEqual(self.browser.current_url, delete_detail_url)

        task = UserTaskLog.objects.get(name="extracted_script_delete.5")
        self.assertIsNotNone(task, "should set up a task")

        task_id = self.browser.find_element_by_id("task_id").get_attribute("value")
        self.assertEqual(str(task.task), task_id)
        redirect_to = self.browser.find_element_by_id("redirect_to").get_attribute(
            "value"
        )
        self.assertEqual("/extractionscripts/delete/", redirect_to)

        # wait for task to finish
        WebDriverWait(self.browser, 30).until(EC.url_changes(delete_detail_url))

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
                f'//*[@id="chem-{chem.pk}"]'
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

    def test_nested_formset(self):
        # the pages being tested include all the RawChem subtypes
        extracted_text = ExtractedText.objects.filter(pk__in=[7, 11, 254780, 5])
        for et in extracted_text:
            qa_url = self.live_server_url + reverse(
                "extracted_text_qa", kwargs={"pk": et.pk}
            )
            self.browser.get(qa_url)
            # open the chemical card
            chem = et.rawchem.first()
            self.browser.find_element_by_xpath(
                f'//*[@id="chem-card-{chem.pk}"]'
            ).click()
            # switch to editing mode
            self.browser.find_element_by_id("btn-toggle-edit").click()
            wait = WebDriverWait(self.browser, 10)

            fu_input = self.browser.find_element_by_id(
                "id_rawchem-0-functional_uses-0-report_funcuse"
            )

            fu_input = wait.until(
                EC.visibility_of_element_located(
                    (By.ID, "id_rawchem-0-functional_uses-0-report_funcuse")
                )
            )
            fu_input.send_keys(" edited")

            save_button = wait.until(EC.element_to_be_clickable((By.ID, "save")))
            save_button.send_keys(Keys.SPACE)

            # the page should reload in non-editing mode

            edit_button = wait.until(
                EC.visibility_of_element_located((By.ID, "btn-toggle-edit"))
            )
            self.assertIn(
                "toggleDetailEdit(true)", edit_button.get_attribute("onclick")
            )

    def test_list_presence_chem_delete(self):
        # make sure that deleting an ExtractedListPresence record doesn't fail
        # if it has related Functional Use
        wait = WebDriverWait(self.browser, 10)
        et = ExtractedText.objects.get(pk=254780)
        chem = et.rawchem.first()

        qa_url = self.live_server_url + reverse(
            "extracted_text_qa", kwargs={"pk": et.pk}
        )
        self.browser.get(qa_url)

        # open the first chemical card
        self.browser.find_element_by_xpath(f'//*[@id="chem-card-{chem.pk}"]').click()

        # delete the first RawChem/ExtractedListPresence record
        delcheck = wait.until(
            EC.element_to_be_clickable((By.ID, "id_rawchem-0-DELETE"))
        )
        delcheck.click()

        # save the page
        save_button = wait.until(EC.element_to_be_clickable((By.ID, "save")))
        save_button.send_keys(Keys.SPACE)

        # the reopened page should not contain the chemical
        accordion = wait.until(EC.visibility_of_element_located((By.ID, "accordion")))
        self.assertNotIn(chem.raw_chem_name, accordion.text)
