from lxml import html

from django.test import TestCase
from dashboard.tests.loader import load_model_objects

from dashboard.models import *

# class DataSourceTest(TestCase):
#
#     def setUp(self):
#         self.objects = load_model_objects()
#         self.client.login(username='Karyn', password='specialP@55word')
#
#         for i in range(27):
#             DataSource.objects.create(title=f'Test_DS_{i}')
#         response = self.client.get(f'/datasources/').content.decode('utf8')
#         print(response)



###############################################################################
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
            DataSource.objects.create(title=f'Test_DS_{i}')
        self.browser.get(self.live_server_url + '/datasources/')
        row_count = len(self.browser.find_elements_by_xpath("//table[@id='sources']/tbody/tr"))
        self.assertEqual(row_count, 25, 'Should be 25 datasources in the table')
