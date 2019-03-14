from lxml import html

from django.test import TestCase
from dashboard.tests.loader import load_model_objects, fixtures_standard
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from dashboard.models import *
from selenium import webdriver
from django.conf import settings
from selenium.webdriver.support.select import Select


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
        Adding a new ExtractedChemical without a unity type should return a validation error
        '''
        # currently "loops" over just a single data document. Other cases can be added
        ets_with_curation = ExtractedText.objects.filter(
            rawchem__dsstox__isnull=False).filter(pk=245401)
        for et in ets_with_curation:
            doc_qa_link = f'/qa/extractedtext/%s/' % et.data_document_id
            self.browser.get(self.live_server_url + doc_qa_link)

            self.browser.find_element_by_xpath(
                '//*[@id="btn-toggle-edit"]').click()
            raw_cas_input = self.browser.find_element_by_xpath(
                '//*[@id="id_rawchem-1-raw_cas"]')
            raw_cas_input.send_keys('test raw cas')
            self.browser.find_element_by_xpath('//*[@id="save"]').click()
            # Check for the error message after clicking Save
            parent_div = self.browser.find_element_by_xpath(
                '//*[@id="id_rawchem-1-raw_cas"]/parent::*')
            card_div = parent_div.find_element_by_xpath(
                '../..')
            self.assertTrue("errorlist" in card_div.get_attribute("innerHTML"))

            # Try editing a new record correctly
            self.browser.find_element_by_xpath(
                '//*[@id="btn-toggle-edit"]').click()
            raw_cas_input = self.browser.find_element_by_xpath(
                '//*[@id="id_rawchem-1-raw_cas"]')
            raw_cas_input.send_keys('test raw cas')
            # The unit_type field is the only required one
            unit_type_select = Select(self.browser.find_element_by_xpath(
                '//*[@id="id_rawchem-1-unit_type"]'))
            unit_type_select.select_by_index(1)

            self.browser.find_element_by_xpath('//*[@id="save"]').click()
            # Check for the absence of an error message after clicking Save
            parent_div = self.browser.find_element_by_xpath(
                '//*[@id="id_rawchem-1-raw_cas"]/parent::*')
            card_div = parent_div.find_element_by_xpath(
                '../..')
            self.assertFalse(
                "errorlist" in card_div.get_attribute("innerHTML"))
