from lxml import html

from django.test import TestCase
from dashboard.tests.loader import load_model_objects, fixtures_standard
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from dashboard.models import *
from selenium import webdriver
from django.conf import settings
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec


def log_karyn_in(object):
    '''
    Log user in for further testing.
    '''
    object.browser.get(object.live_server_url + '/login/')
    body = object.browser.find_element_by_tag_name('body')
    object.assertIn('Please sign in', body.text)
    username_input = object.browser.find_element_by_name("username")
    username_input.send_keys('Karyn')
    password_input = object.browser.find_element_by_name("password")
    password_input.send_keys('specialP@55word')
    object.browser.find_element_by_class_name('btn').click()


class TestEditsWithSeedData(StaticLiveServerTestCase):
    fixtures = fixtures_standard

    def setUp(self):
        if settings.TEST_BROWSER == 'firefox':
            self.browser = webdriver.Firefox()
        else:
            self.browser = webdriver.Chrome()
        log_karyn_in(self)

    def tearDown(self):
        self.browser.quit()

    def test_break_curation(self):
        '''
        Changing the raw_cas or raw_chemname on a RawChem record with a related DssToxLookup should cause
        the relationship to be deleted.
        '''
        # currently uses a single data document
        ets_with_curation = ExtractedText.objects.filter(
            rawchem__dsstox__isnull=False).filter(pk=245401)
        for et in ets_with_curation:
            doc_qa_link = f'/qa/extractedtext/%s/' % et.data_document_id
            self.browser.get(self.live_server_url + doc_qa_link)

            rc_id = self.browser.find_element_by_xpath(
                '//*[@id="id_rawchem-0-rawchem_ptr"]').get_attribute('value')
            true_cas = self.browser.find_element_by_xpath(
                '//*[@id="id_rawchem-0-true_cas"]').get_attribute('value')
            rc = RawChem.objects.get(pk=rc_id)
            self.assertEqual(true_cas, rc.dsstox.true_cas,
                             'The displayed True CAS should match the object attribute')
            self.browser.find_element_by_xpath(
                '//*[@id="btn-toggle-edit"]').click()
            raw_cas_input = self.browser.find_element_by_xpath(
                '//*[@id="id_rawchem-0-raw_cas"]')
            raw_cas_input.send_keys('changed cas')
            self.browser.find_element_by_xpath('//*[@id="save"]').click()
            rc = RawChem.objects.get(pk=rc_id)   # reload the rawchem record
            self.assertEqual(
                None, rc.dsstox, 'The same rawchem record should now have nothing in its dsstox link')

    def test_new_chem(self):
        '''
        Adding a new ExtractedChemical without a unit type should return a validation error
        '''
        # currently "loops" over just a single data document. Other cases can be added
        ets_with_curation = ExtractedText.objects.filter(
            rawchem__dsstox__isnull=False).filter(pk=245401)
        for et in ets_with_curation:
            doc_qa_link = f'/qa/extractedtext/%s/' % et.data_document_id
            self.browser.get(self.live_server_url + doc_qa_link)

            self.browser.find_element_by_xpath(
                '//*[@id="btn-toggle-edit"]').click()
            # wait for the Save button to be clickable
            wait = WebDriverWait(self.browser, 10)
            save_button = wait.until(
                ec.element_to_be_clickable((By.XPATH, "//*[@id='save']")))
            # edit the Raw CAS field
            raw_cas_input = self.browser.find_element_by_xpath(
                '//*[@id="id_rawchem-1-raw_cas"]')
            raw_cas_input.send_keys('test raw cas')
            # Save the edits
            save_button.send_keys("\n")
            # Check for the error message after clicking Save
            wait.until(ec.visibility_of(self.browser.find_element_by_xpath(
                '//*[@id="id_rawchem-1-raw_cas"]/parent::*')))
            parent_div = self.browser.find_element_by_xpath(
                '//*[@id="id_rawchem-1-raw_cas"]/parent::*')
            card_div = parent_div.find_element_by_xpath(
                '../..')
            self.assertTrue("errorlist" in card_div.get_attribute("innerHTML"))

            # Try editing a new record correctly
            self.browser.find_element_by_xpath(
                '//*[@id="btn-toggle-edit"]').click()
            # wait for the Save button to be clickable
            wait = WebDriverWait(self.browser, 10)
            save_button = wait.until(
                ec.element_to_be_clickable((By.XPATH, "//*[@id='save']")))
            raw_cas_input = self.browser.find_element_by_xpath(
                '//*[@id="id_rawchem-1-raw_cas"]')
            raw_cas_input.send_keys('test raw cas')
            # The unit_type field is the only required one
            unit_type_select = Select(self.browser.find_element_by_xpath(
                '//*[@id="id_rawchem-1-unit_type"]'))
            unit_type_select.select_by_index(1)

            save_button.send_keys("\n")
            # Check for the absence of an error message after clicking Save
            parent_div = self.browser.find_element_by_xpath(
                '//*[@id="id_rawchem-1-raw_cas"]/parent::*')
            card_div = parent_div.find_element_by_xpath(
                '../..')
            self.assertFalse(
                "errorlist" in card_div.get_attribute("innerHTML"))

    def test_redirects(self):
        '''
        Editing the data document type should return the user to the page on which the edits were made
        '''
        for doc_id in [7]:
            # QA Page
            doc_qa_link = f'/qa/extractedtext/%s/' % doc_id
            self.browser.get(self.live_server_url + doc_qa_link)
            doc_type_select = Select(self.browser.find_element_by_xpath(
                '//*[@id="id_document_type"]'))
            option = doc_type_select.first_selected_option
            doc_type_select.select_by_visible_text("ingredient disclosure")
            self.assertIn(doc_qa_link, self.browser.current_url)

            # Data Document Detail Page
            doc_detail_link = f'/datadocument/%s/' % doc_id
            self.browser.get(self.live_server_url + doc_detail_link)
            doc_type_select = Select(self.browser.find_element_by_xpath(
                '//*[@id="id_document_type"]'))
            doc_type_select.select_by_visible_text("MSDS")
            self.assertIn(doc_detail_link, self.browser.current_url)

    def test_qa_approval(self):
        '''
        Test the QA process in the browser
        1. Open the QA page for an ExtractedText record
        2. Edit one of the child records
        3. Attempt to approve the document without a QA note
        4. Add a note
        5. Approve 
        '''
        for doc_id in [7,      # Composition
                       5,      # Functional Use
                       254781, # Chemical Presence List
                       354783, # HHE Report 
                       ]: 
            # QA Page
            qa_url = self.live_server_url + f'/qa/extractedtext/{doc_id}/'
            self.browser.get(qa_url)
            # Activate the edit mode
            self.browser.find_element_by_xpath(
                '//*[@id="btn-toggle-edit"]').click()

            # Modify the first raw_chem_name field's value
            #  
            raw_chem = self.browser.find_element_by_xpath(
                '//*[@id="id_rawchem-0-raw_chem_name"]')
            # Wait for the field to be editable
            wait = WebDriverWait(self.browser, 10)
            raw_chem_name_field = wait.until(ec.element_to_be_clickable(
                (By.XPATH, "//*[@id='id_rawchem-0-raw_chem_name']")))

            old_raw_chem_name = raw_chem_name_field.get_attribute('value')

            # Get the detailed child record's ID
            rawchem_id_field = self.browser.find_element_by_xpath(
                '//*[@id="id_rawchem-0-rawchem_ptr"]')
            rawchem_id = rawchem_id_field.get_attribute('value')
            # print(rawchem_id)

            raw_chem_name_field.send_keys(' edited')
            # save changes
            self.browser.find_element_by_xpath('//*[@id="save"]').click()

            # Confirm the changes in the ORM
            rc = RawChem.objects.get(pk=rawchem_id)
            self.assertEqual(rc.raw_chem_name, f'%s edited' %
                             old_raw_chem_name, 'The raw_chem_name field should have changed')

            et = ExtractedText.objects.get(pk=doc_id)
            # print(et.data_document.data_group.group_type)
            self.assertTrue(
                et.qa_edited, 'The qa_edited attribute should be True')

            # Click Approve without any notes and confirm validation failure
            self.browser.find_element_by_xpath('//*[@id="approve"]').click()
            # The QA notes field should be invalid
            qa_notes_field = self.browser.find_element_by_xpath(
                '//*[@id="id_qa_notes"]')
            self.assertIn('is-invalid', qa_notes_field.get_attribute('class'))
            et.refresh_from_db()
            self.assertFalse(
                et.qa_checked, 'The qa_checked attribute should be False')

            # Add the mandatory QA note
            qa_notes_field.send_keys('Some QA Notes')
            # Click "Approve" again
            self.browser.find_element_by_xpath('//*[@id="approve"]').click()
            et.refresh_from_db()
            self.assertTrue(
                et.qa_checked, 'The qa_checked attribute should be True')



