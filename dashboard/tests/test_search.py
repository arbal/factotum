import os
import csv
import time
import collections
import json
import re
import inspect
from selenium import webdriver
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys


from django.conf import settings
from django.utils import timezone
from django.test import TestCase, LiveServerTestCase, override_settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from dashboard.models import (DataGroup, DataSource, DataDocument,
                              Script, ExtractedText, Product, PUC, ProductDocument, ProductToPUC)

from haystack import connections
from haystack.query import SearchQuerySet
from django.core.management import call_command
from haystack.management.commands import update_index

from django.db import DEFAULT_DB_ALIAS, connection, connections, transaction
from django.test.utils import (
    CaptureQueriesContext, ContextList, compare_xml, modify_settings,
    override_settings,
)


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

class RollbackStaticLiveServerTestCase(StaticLiveServerTestCase):
    """Because StaticLiveServerTestCase extends TransactionTestCase, it lacks \
    the efficient rollback approach of TestCase. TransactionTestCase loads the \
    fixtures with every test method and destroys the test database after each one.\
    The following methods override this slow behavior in favor of TestCase's \
    rollback approach. 
    """
    @classmethod
    def setUpClass(cls):
        """Load the fixtures at the beginning of the class"""
        super().setUpClass()
        if cls.fixtures:
            #print('loading fixtures')
            for db_name in cls._databases_names(include_mirrors=False):
                try:
                    call_command('loaddata', *cls.fixtures, **{'verbosity': 0, 'database': db_name})
                except Exception:
                    raise

    def _fixture_setup(self):
        for db_name in self._databases_names(include_mirrors=False):
            # Reset sequences
            if self.reset_sequences:
                self._reset_sequences(db_name)

            # If we need to provide replica initial data from migrated apps,
            # then do so.
            if self.serialized_rollback and hasattr(connections[db_name], "_test_serialized_contents"):
                if self.available_apps is not None:
                    apps.unset_available_apps()
                connections[db_name].creation.deserialize_db_from_string(
                    connections[db_name]._test_serialized_contents
                )
                if self.available_apps is not None:
                    apps.set_available_apps(self.available_apps)

    def _fixture_teardown(self):
        """TransactionTestCase would flush the database here - this override avoids it"""
        # Allow TRUNCATE ... CASCADE and don't emit the post_migrate signal
        # when flushing only a subset of the apps
        for db_name in self._databases_names(include_mirrors=False):
            # Flush the database
            inhibit_post_migrate = (
                self.available_apps is not None or
                (   # Inhibit the post_migrate signal when using serialized
                    # rollback to avoid trying to recreate the serialized data.
                    self.serialized_rollback and
                    hasattr(connections[db_name], '_test_serialized_contents')
                )
            )



class SearchTests(RollbackStaticLiveServerTestCase):
    fixtures = ['00_superuser.yaml', '01_lookups.yaml',
    '02_datasource.yaml' , '03_datagroup.yaml', '04_PUC.yaml',
    '05_product.yaml', '06_datadocument.yaml' , '07_script.yaml', 
     '08_extractedtext.yaml','09_productdocument.yaml','10_extractedchemical','11_dsstoxsubstance']

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # see if fixtures have been loaded yet
        print("DataSource objects: {}".format(DataSource.objects.count()))
        index_start = time.time()
        update_index.Command().handle(using=['test_index'], remove=True)
        index_elapsed = time.time() - index_start

    def setUp(self):
        if settings.TEST_BROWSER == 'firefox':
            self.browser = webdriver.Firefox()
        else:
            self.browser = webdriver.Chrome(settings.CHROMEDRIVER_PATH) 
        self.test_start = time.time()
        log_karyn_in(self)

    def tearDown(self):
        #print('  running test case tearDown()')
        self.test_elapsed = time.time() - self.test_start
        self.browser.quit()
        print('\nFinished with ' + self._testMethodName)
        print("Test case took {:.2f}s".format(self.test_elapsed)) 

    def test_elasticsearch(self):
        # Implement faceted search within application. Desire ability to search on Products by title,
        # with the following two facets
        #
        # Data documents, by type of data document
        # (e.g. no data document, MSDS, SDS, ingredient list, etc.)
        # Product category, by general category (e.g., no product
        # category, list of ~12 general categories)
        #
        # Search bar appears on far right side of the navigation bar, on every page of the application.
        # User enters a product title in the search bar. User is then taken to a landing page with
        # search results on product title, with the two facets visible on the left side of the page.

        # TODO: fix to use new Product-to-PUC foreign key relationship
        # example results:
        # http://127.0.0.1:9200/_search?q=lubricity&brand_name=British%20Petroleum

        p1 = Product.objects.get(pk=22)
        pc252 = ProductCategory.objects.get(pk=252)
        p1.prod_cat = pc252
        p1.save()
        # update the search engine index
        update_index.Command().handle(using=['test_index'],remove=True)

        # Check for the elasticsearch engine
        self.browser.get('http://127.0.0.1:9200/')
        self.assertIn("9200", self.browser.current_url)
        self.assertIn("elasticsearch", self.browser.page_source,
                      "The search engine's server needs to be running")
        # if a Product object has a PUC assigned, that PUC should appear in the facet index
        sqs = SearchQuerySet().using('test_index').facet('prod_cat')
        self.assertIn('insect', json.dumps(sqs.facet_counts()),
                      'The search engine should return "["Pesticides - insect repellent - insect repellent - skin", 1]" among the product category facets.')

        # use the input box to enter a search query
        self.browser.get(self.live_server_url)
        searchbox = self.browser.find_element_by_id('q')
        searchbox.send_keys('Skinsations')
        searchbox.send_keys(Keys.RETURN)
        self.assertIn("Skinsations", self.browser.current_url,
                      'The URL should contain the search string')
        facetcheck = self.browser.find_element_by_xpath(
            '/html/body/div/div/div/div[1]')
        self.assertIn('insect', facetcheck.text,
                      'The faceting controls should include a "Pesticides - insect repellent" entry')
        facetcheck = self.browser.find_element_by_id('Pesticides-insectrepellent-insectrepellent-skin')
        facetcheck.click()
        facetapply = self.browser.find_element_by_id('btn-apply-filters')
        facetapply.click()
        self.assertIn("insect%20repellent",
                      self.browser.current_url, 'The URL should contain the facet search string') 

