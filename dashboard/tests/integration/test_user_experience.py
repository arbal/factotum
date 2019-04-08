from lxml import html
from django.test import TestCase
from dashboard.tests.loader import load_model_objects
from dashboard.models import *
import os
import csv
import time
import unittest
import collections
import json
import re
from selenium import webdriver
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from dashboard.models import *


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


class TestIntegration(StaticLiveServerTestCase):

    def setUp(self):
        self.objects = load_model_objects()
        if settings.TEST_BROWSER == 'firefox':
            self.browser = webdriver.Firefox()
        else:
            self.browser = webdriver.Chrome()
        log_karyn_in(self)

    def tearDown(self):
        self.browser.quit()

    def test_hem(self):
        for i in range(27):
            ds = DataSource.objects.create(title=f'Test_DS_{i}')
        list_url = self.live_server_url + '/datasources/'
        self.browser.get(list_url)
        row_count = len(self.browser.find_elements_by_xpath("//table[@id='sources']/tbody/tr"))
        self.assertEqual(row_count, 25, 'Should be 25 datasources in the table')
        # go to edit page from datasource list
        self.browser.find_element_by_xpath('//*[@title="edit"]').click()
        btn = self.browser.find_element_by_name('cancel')
        self.assertEqual(btn.get_attribute("href"), list_url,
                         "User should go back to list view when clicking cancel")
        self.browser.find_element_by_name('submit').click()
        self.assertIn('/datasource/', self.browser.current_url,
                      "User should always return to detail page after submit")
        detail_url = self.live_server_url + f'/datasource/{ds.pk}'
        self.browser.get(detail_url)
        # go to edit page from datasource detail
        self.browser.find_element_by_xpath('//*[@title="edit"]').click()
        btn = self.browser.find_element_by_name('cancel')
        self.assertEqual(btn.get_attribute("href"), detail_url,
                         "User should go back to detail view when clicking cancel")
        self.browser.find_element_by_name('submit').click()
        self.assertIn('/datasource/', self.browser.current_url,
                      "User should always return to detail page after submit")

        num_pucs = len(PUC.objects.filter(kind='FO'))
        self.browser.get(self.live_server_url)
        import time
        time.sleep(3)  # or however long you think it'll take you to scroll down to bubble chart
        bubbles = self.browser.find_elements_by_class_name('bubble')
        self.assertEqual(num_pucs, len(bubbles), ('There should be a circle'
                                                  'drawn for every PUC'))

    def test_datagroup(self):
        list_url = self.live_server_url + '/datagroups/'
        self.browser.get(list_url)
        self.browser.find_element_by_xpath('//*[@title="edit"]').click()
        btn = self.browser.find_element_by_name('cancel')
        self.assertEqual(btn.get_attribute("href"), list_url,
                         "User should go back to list view when clicking cancel")

        dg = DataGroup.objects.first()
        ds_detail_url = f'{self.live_server_url}/datasource/{dg.data_source.pk}'
        self.browser.get(ds_detail_url)
        self.browser.find_elements_by_xpath('//*[@title="edit"]')[1].click()
        btn = self.browser.find_element_by_name('cancel')
        self.assertEqual(btn.get_attribute("href"), ds_detail_url,
                         "User should go back to detail view when clicking cancel")

        dg_detail_url = f'{self.live_server_url}/datagroup/{dg.pk}/'
        self.browser.get(dg_detail_url)
        self.browser.find_element_by_xpath('//*[@title="edit"]').click()
        btn = self.browser.find_element_by_name('cancel')
        self.assertEqual(btn.get_attribute("href"), dg_detail_url,
                         "User should go back to detail view when clicking cancel")

        edit_url = f'{self.live_server_url}/datagroup/edit/{dg.pk}/'
        self.browser.get(edit_url)
        self.browser.find_element_by_name('cancel').click()
        self.assertIn('/datagroups/', self.browser.current_url,
                      "User should always return to detail page after submit")

    def test_product(self):
        p = self.objects.p
        puc = self.objects.puc
        tag = self.objects.pt
        PUCToTag.objects.create(content_object=puc, tag=tag)
        ProductToPUC.objects.create(product=p, puc=puc)
        url = self.live_server_url + f'/product/{p.pk}/'
        self.browser.get(url)
        submit = self.browser.find_element_by_id('tag_submit')
        self.assertFalse(submit.is_enabled(), "Button should be disabled")
        tag = self.browser.find_element_by_class_name('taggit-tag')
        tag.click()
        self.assertTrue(submit.is_enabled(), "Button should be enabled")

    def test_field_exclusion(self):
        doc = self.objects.doc
        # The element should not appear on the QA page
        qa_url = self.live_server_url + f'/qa/extractedtext/{doc.pk}/'
        self.browser.get(qa_url)
        with self.assertRaises(NoSuchElementException):
            self.browser.find_element_by_xpath('//*[@id="id_rawchem-0-weight_fraction_type"]')
        with self.assertRaises(NoSuchElementException):
            self.browser.find_element_by_xpath('//*[@id="id_rawchem-0-true_cas"]')
        with self.assertRaises(NoSuchElementException):
            self.browser.find_element_by_xpath('//*[@id="id_rawchem-0-true_chemname"]')
        with self.assertRaises(NoSuchElementException):
            self.browser.find_element_by_xpath('//*[@id="id_rawchem-0-SID"]')
        # make sure the test can pick up one that should be there
        try:
            self.browser.find_element_by_xpath('//*[@id="id_rawchem-0-raw_cas"]')
        except NoSuchElementException:
            self.fail("Absence of raw_cas element raised exception")

        # The element should appear on the datadocument page
        dd_url = self.live_server_url + f'/datadocument/{doc.pk}/'
        self.browser.get(dd_url)
        try:
            self.browser.find_element_by_xpath('//*[@id="id_rawchem-0-weight_fraction_type"]')
        except NoSuchElementException:
            self.fail("Absence of weight_fraction_type element raised exception")

