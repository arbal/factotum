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
from django.urls import reverse
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from dashboard.models import (DataGroup, DataSource, DataDocument,
                              Script, ExtractedText, Product, ProductCategory, ProductDocument, SourceType)

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


def connections_support_transactions():
    """Force these tests to assume that we're using a transaction-capable database backend."""
    # return all(conn.features.supports_transactions for conn in connections.all())
    return True


class RollbackStaticLiveServerTestCase(StaticLiveServerTestCase):
    """Because StaticLiveServerTestCase extends TransactionTestCase, it lacks \
    the efficient rollback approach of TestCase. TransactionTestCase loads the \
    fixtures with every test method and destroys the test database after each one.\
    The following methods override this slow behavior in favor of TestCase's \
    rollback approach.
    """
    @classmethod
    def _enter_atomics(cls):
        """Open atomic blocks for multiple databases."""
        atomics = {}
        for db_name in cls._databases_names():
            atomics[db_name] = transaction.atomic(using=db_name)
            atomics[db_name].__enter__()
        return atomics

    @classmethod
    def _rollback_atomics(cls, atomics):
        """Rollback atomic blocks opened by the previous method."""
        for db_name in reversed(cls._databases_names()):
            transaction.set_rollback(True, using=db_name)
            atomics[db_name].__exit__(None, None, None)

    @classmethod
    def setUpClass(cls):
        """Load the fixtures at the beginning of the class"""
        super().setUpClass()
        if cls.fixtures:
            #print('loading fixtures')
            for db_name in cls._databases_names(include_mirrors=False):
                try:
                    call_command('loaddata', *cls.fixtures, **
                                 {'verbosity': 0, 'database': db_name})
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


class FunctionalTests(RollbackStaticLiveServerTestCase):
    fixtures = ['00_superuser.yaml', '01_lookups.yaml',
    '02_datasource.yaml' , '03_datagroup.yaml', '04_productcategory.yaml',
    '05_product.yaml', '06_datadocument.yaml' , '07_script.yaml',
     '08_extractedtext.yaml','09_productdocument.yaml']

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def setUp(self):
        if settings.TEST_BROWSER == 'firefox':
            self.browser = webdriver.Firefox()
        else:
            self.browser = webdriver.Chrome()
        self.test_start = time.time()
        log_karyn_in(self)
        print('\n------ setUp() for ' + self._testMethodName)
        #print("\nDataGroup objects when method runs: {}".format(DataGroup.objects.count()))
        #print('\nExtractedText objects where qa_checked = True: ')
        # print(Script.objects.get(pk=6).extractedtext_set.filter(qa_checked=True).values('pk','prod_name','qa_checked'))
        # print('\n------\n')

    def tearDown(self):
        #print('  running test case tearDown()')
        self.test_elapsed = time.time() - self.test_start
        self.browser.quit()
        print('\n------ tearDown() for ' + self._testMethodName)
        #print('\nExtractedText objects where qa_checked = True: ')
        # print(Script.objects.get(pk=6).extractedtext_set.filter(qa_checked=True).values('pk','prod_name','qa_checked'))
        #print('\nDataGroup objects in test database: ')
        # print(DataGroup.objects.count())
        print("Test case took {:.2f}s".format(self.test_elapsed))
        print(' ')

    def test_data_source_name(self):
        dspk = DataSource.objects.filter(title='Walmart MSDS')[0].pk
        self.browser.get(self.live_server_url + '/datasource/' + str(dspk))
        h1 = self.browser.find_element_by_name('title')
        self.assertIn('Walmart MSDS', h1.text,
                      'The h1 text should include "Walmart MSDS"')

    # When a new data source is entered, the data source is automatically
    # assigned the state 'awaiting triage.'
    def test_state_and_priority(self):
        dspk = DataSource.objects.get(title='Walmart MSDS').id
        valid_states = ['Awaiting Triage', 'In Progress', 'Complete', 'Stale']
        valid_priorities = ['High', 'Medium', 'Low']
        self.browser.get(self.live_server_url + '/datasource/' + str(dspk))
        state = self.browser.find_element_by_name('state')
        self.assertIn(state.text, valid_states)
        self.assertIn('Awaiting Triage', state.text)
        select = Select(self.browser.find_element_by_name('priority'))
        self.assertEqual([o.text for o in select.options], valid_priorities)
        selected_option = select.first_selected_option
        self.assertIn(selected_option.text, valid_priorities)

    def test_datagroup_list_length(self):
        b = len(DataGroup.objects.filter(data_source_id=1))
        self.browser.get(self.live_server_url + '/datasource/1')
        row_count = len(self.browser.find_elements_by_xpath(
            "//table[@id='groups']/tbody/tr"))
        self.assertEqual(
            b, row_count, 'Does the number of objects with the data_source_id of 1 (left side) match number of rows in the table (right side)?')

    def test_DataTables(self):
        self.browser.get(self.live_server_url + '/datasources/')
        wrap_div = self.browser.find_element_by_class_name(
            'dataTables_wrapper')
        self.assertIn("Show", wrap_div.text, 'DataTables missing...')

    # Data Groups

    def test_data_group_name(self):
        dgpk = DataGroup.objects.filter(name='Walmart MSDS 1')[0].pk
        self.browser.get(self.live_server_url + '/datagroup/' + str(dgpk))
        h1 = self.browser.find_element_by_name('title')
        self.assertIn('Walmart MSDS 1', h1.text)
        rows = self.browser.find_elements_by_xpath(
            "//table[@id='registered']/tbody/tr")
        docs = DataDocument.objects.filter(data_group=dgpk)
        self.assertEqual(len(rows), len(
            docs), 'This table needs to be the entire set of data documents for the group for downloading CSV.')

    def create_data_group(self, data_source, testusername='Karyn',
                          name='Walmart MSDS 3',
                          description=('Another data group, '
                                       'added programatically')):
        source_csv = open('./sample_files/walmart_msds_3.csv', 'rb')
        return DataGroup.objects.create(name=name,
                                        description=description,
                                        data_source=data_source,
                                        downloaded_by=User.objects.get(
                                            username=testusername),
                                        downloaded_at=timezone.now(),
                                        download_script=None,
                                        csv=SimpleUploadedFile('walmart_msds_3.csv', source_csv.read()))

    # def test_edit_persistence(self):
    #    print("DataGroup objects in test_edit_persistence: {}".format(DataGroup.objects.count()))

    def upload_pdfs(self):
        store = settings.MEDIA_URL + self.dg.dgurl()
        pdf1_name = '0ffeb4ae-2e36-4400-8cfc-a63611011d44.pdf'
        pdf2_name = '1af3fa0f-edf3-4a41-bcec-7436d0689bd8.pdf'
        local_pdf = open('./sample_files/' + pdf1_name, 'rb')
        fs = FileSystemStorage(store + '/pdf')
        fs.save(pdf1_name, local_pdf)
        local_pdf = open('./sample_files/' + pdf2_name, 'rb')
        fs = FileSystemStorage(store + '/pdf')
        fs.save(pdf2_name, local_pdf)
        return [pdf1_name, pdf2_name]

    def create_data_documents(self, data_group, source_type):
        dds = []
        #pdfs = [f for f in os.listdir('/media/' + self.dg.dgurl() + '/pdf') if f.endswith('.pdf')]
        # pdfs
        with open(data_group.csv.path) as dg_csv:
            table = csv.DictReader(dg_csv)
            errors = []
            count = 0
            for line in table:  # read every csv line, create docs for each
                count += 1
                if line['filename'] == '':
                    errors.append(count)
                if line['title'] == '':  # updates title in line object
                    line['title'] = line['filename'].split('.')[0]
                dd = DataDocument.objects.create(filename=line['filename'],
                                                 title=line['title'],
                                                 product_category=line['product'],
                                                 url=line['url'],
                                                 matched=line['filename'] in self.pdfs,
                                                 data_group=data_group,
                                                 source_type=source_type)
                dds.append(dd)
            return dds

    # creation of another DataGroup from csv and pdf sources
    #@transaction.atomic
    def test_new_data_group(self):
        # DataGroup, created using the model layer
        dg_count_before = DataGroup.objects.count()
        ds = DataSource.objects.filter(title='Walmart MSDS')[0]
        self.dg = self.create_data_group(data_source=ds)
        st = SourceType.objects.create(title="title")

        dg_count_after = DataGroup.objects.count()
        print('DataGroup count after test_new_data_group: {}'.format(dg_count_after))
        self.assertEqual(dg_count_after, dg_count_before + 1,
                         "Confirm the DataGroup object has been created")
        new_dg_pk = self.dg.pk
        self.pdfs = self.upload_pdfs()
        self.dds = self.create_data_documents(self.dg, st)

        # Use the browser layer to confirm that the object has been created
        self.browser.get('%s%s%s' %
                         (self.live_server_url, '/datagroup/', new_dg_pk))
        self.assertEqual('factotum', self.browser.title,
                         "Testing open of show page for new data group")

        self.browser.get(self.live_server_url + reverse('data_group_detail',
                                                        kwargs={'pk': self.dg.pk}))
        self.assertEqual('factotum', self.browser.title)
        h1 = self.browser.find_element_by_name('title')
        self.assertIn('Walmart MSDS ', h1.text)

        # Use the browser layer to delete the DataGroup object
        # deleting the DataGroup should clean up the file system
        self.browser.get('%s%s%s' % (self.live_server_url,
                                     '/datagroup/delete/', new_dg_pk))
        del_button = self.browser.find_elements_by_xpath(('/html/body/div/form/'
                                                          'input[2]'))[0]
        del_button.click()
        self.assertEqual(DataGroup.objects.count(), dg_count_before,
                         "Confirm the DataGroup object has been deleted")

    def test_pagination(self):
        # The data group detail page uses server-side pagination to display the
        # related data documents
        dgpk = DataGroup.objects.get(name='Walmart MSDS 2').id
        self.browser.get('%s%s%s' %
                         (self.live_server_url, '/datagroup/', str(dgpk)))
        pagebox = self.browser.find_element_by_xpath(
            "/html/body/div[1]/nav/ul/li[1]/span")
        self.assertIn('Page 1', pagebox.text,
                      "Confirm the current page navigation box displays 'Page 1 of [some number]'")
        nextbox = self.browser.find_element_by_xpath(
            '/html/body/div[1]/nav/ul/li[2]/a')
        nextbox.click()
        self.assertIn("?page=2", self.browser.current_url,
                      'The newly opened URL should contain the new page number')

    def test_unlinked_documents(self):
        self.browser.get(self.live_server_url + '/product_curation/')
        src_title = self.browser.find_elements_by_xpath(
            '//*[@id="products"]/tbody/tr/td[1]/a')[0]
        ds = DataSource.objects.get(title=src_title.text)
        un_link = self.browser.find_elements_by_xpath(
            '//*[@id="products"]/tbody/tr/td[1]/a')[0]
        self.assertEqual(un_link.get_attribute("href").split('/')[-1],
                         str(ds.pk))

    def test_link_product(self):
        dgpk = DataGroup.objects.filter(name='Walmart MSDS 2')[0].pk
        self.browser.get(self.live_server_url +
                         '/link_product_list/' + str(dgpk))
        create_prod_link = self.browser.find_element_by_xpath(
            '//*[@id="products"]/tbody/tr[1]/td[2]/a')
        create_prod_link.click()
        upc = self.browser.find_element_by_name('upc')
        self.assertIn('stub_', upc.get_attribute('value'), 'Default value of upc input should be the stub_xx value.')
        title_input = self.browser.find_element_by_xpath('//*[@id="id_title"]')
        manufacturer_input = self.browser.find_element_by_xpath(
            '//*[@id="id_manufacturer"]')
        brand_name_input = self.browser.find_element_by_xpath(
            '//*[@id="id_brand_name"]')

        title_input.send_keys('A Product Title')
        manufacturer_input.send_keys('A Product Manufacturer')
        brand_name_input.send_keys('A Product Brand Name')
        # get the data document's ID from the URL, for later use
        dd_pk = re.search('(?P<pk>\d+)$', self.browser.current_url).group(0)

        save_button = self.browser.find_element_by_xpath(
            '/html/body/div[1]/form/button')
        save_button.click()
        # Saving the product should return the browser to the list of documents without products
        self.assertIn("link_product_list", self.browser.current_url)
        # The URL of the link_product_list page should be keyed to the DataGroup, not DataSource
        self.assertEqual(self.live_server_url + '/link_product_list/' +
                         str(dgpk), self.browser.current_url)

        # check at the model level to confirm that the edits have been applied
        # self.assertEqual(dd_pk, 'x')
        pd = ProductDocument.objects.get(document=dd_pk)
        p = Product.objects.get(pk=pd.product.id)
        self.assertEqual('A Product Title', p.title)

    def test_PUC_assignment(self):
        self.browser.get(self.live_server_url + '/product_curation/')
        src_title = self.browser.find_elements_by_xpath(
            '//*[@id="products"]/tbody/tr[3]/td[1]/a')[0]
        ds = DataSource.objects.get(title=src_title.text)
        self.assertEqual(ds.title, 'Home Depot - ICF',
                         'Check the title of the group')
        puc_link = self.browser.find_elements_by_xpath(
            '//*[@id="products"]/tbody/tr[3]/td[4]')[0]
        products_missing_PUC = str(
            len(ds.source.filter(prod_cat__isnull=True)))
        self.assertEqual(puc_link.text, products_missing_PUC, ('The Assign PUC \
                                    link should display # of Products without a PUC'))

    def test_puc(self):

        # As Karyn the Curator
        # I want the ability to assign product categories (PUCs) to a product
        # So that I can more easily navigate through products if they are grouped.

        # From the assignment of product category
        # Click button, form appears which shows you a pdf icon allowing you to view pdf,
        # product name (Product.title), auto complete box for PUC - when you start typing
        # auto complete looks at general, specific, product family to match what the user
        # is typing (auto complete should work like Google), expect minimum of three
        # characters before auto complete appears
        ppk = Product.objects.get(title=' Skinsations Insect Repellent').id
        self.browser.get('%s%s%s' %
                         (self.live_server_url, '/product_puc/', str(ppk)))
        h2 = self.browser.find_element_by_xpath('/html/body/div/h2').text
        self.assertIn(h2, Product.objects.get(pk=ppk).title,
                      'The <h2> text should be within the .title of the product'
                      ' (accounting for padding spaces)')

        self.assertEqual(1, Product.objects.filter(pk=ppk).count(),
                         "There should be one object with the pk of interest")

        puc_before = Product.objects.get(pk=ppk).prod_cat
        self.assertEqual(puc_before, None, "There should be no assigned PUC")

        puc_selector = self.browser.find_element_by_xpath(
            '//*[@id="id_prod_cat"]')
        puc_selector = self.browser.find_element_by_xpath(
            '//*[@id="select2-id_prod_cat-container"]')
        puc_sibling = self.browser.find_element_by_xpath(
            '//*[@id="id_prod_cat"]/following::*')
        puc_sibling.click()
        print('clicked on product sibling link')

        #wait_for_element(self, "select2-search__field", "class").click()
        puc_input = self.browser.find_element_by_class_name(
            'select2-search__field')
        puc_input.send_keys('insect')

        # The driver cannot immediately type into the input box - it needs
        # to load an element first, as explained here:
        # https://stackoverflow.com/questions/34422274/django-selecting-autocomplete-light-choices-with-selenium

        wait_for_element(self,
                         '//*[@id="select2-id_prod_cat-results"]/li[3]',
                         "xpath").click()
        puc_selector = self.browser.find_element_by_xpath(
            '//*[@id="select2-id_prod_cat-container"]')
        self.assertEqual(puc_selector.text, 'Pesticides - insect repellent - insect repellent - skin',
                         'The PUC selector value should be "Pesticides - insect repellent - insect repellent - skin"')

        submit_button = self.browser.find_element_by_id('btn-assign-puc')
        submit_button.click()
        # Open the product page and confirm the PUC has changed
        self.browser.get('%s%s%s' % (self.live_server_url, '/product/', ppk))
        puc_after = self.browser.find_element_by_id('prod_cat')
        self.assertNotEqual(puc_before, puc_after,
                            "The object's prod_cat should have changed")
        # Confirm that the puc_assigned_usr has been set to the current user
        puc_assigned_usr_after = self.browser.find_element_by_id(
            'puc_assigned_usr').text
        self.assertEqual(puc_assigned_usr_after, 'Karyn',
                         "The PUC assigning user should have changed")

    def test_cancelled_puc_assignment(self):

        # Bug report in issue #155
        # When on the Product Curation Page, I click Assign Puc.
        # I decide that I can not find a PUC and press cancel and get this error:

        # DataSource matching query does not exist.
        # data/code/factotum/dashboard/views/product_curation.py in category_assignment
        # ds = DataSource.objects.get(pk=pk)
        # pk | '1'
        # request | <WSGIRequest: GET '/category_assignment/1'>
        # template_name | 'product_curation/category_assignment.html'

        # This was happening because the destination URL for the Cancel
        # button was being built with the Product's ID instead of the
        # Product's DataSource's ID.
        ppk = Product.objects.get(title=' Skinsations Insect Repellent').id
        prod = Product.objects.get(pk=ppk)
        ds_id = prod.data_source.id
        ds = DataSource.objects.get(pk=ds_id)
        self.browser.get('%s%s%s' %
                         (self.live_server_url, '/product_puc/', ppk))
        cancel_a = self.browser.find_element_by_xpath(
            '/html/body/div/div/form/a')
        # find out the path that the Cancel button will use
        cancel_a_href = cancel_a.get_attribute("href")
        # open that page
        self.browser.get(cancel_a_href)
        # make sure it shows a DataSource
        h2 = self.browser.find_element_by_xpath(
            '/html/body/div/div[1]/h2').text
        self.assertIn(ds.title, h2,
                      'The <h2> text should equal the .title of the DataSource')

    def test_scoreboard(self):

        # A link in the nav bar to the QA Home page
        self.browser.get('%s%s' % (self.live_server_url, ''))
        nav_html = self.browser.find_element_by_xpath(
            '//*[@id="navbarCollapse"]/ul').get_attribute('innerHTML')
        self.assertIn('href="/qa/"', nav_html,
                      'The link to /qa/ must be in the nav list')

        self.browser.get('%s%s' % (self.live_server_url, '/qa'))
        scriptcount = Script.objects.filter(script_type='EX').count()

        # A Table on the QA home page
        row_count = len(self.browser.find_elements_by_xpath(
            "//table[@id='extraction_script_table']/tbody/tr"))
        self.assertEqual(scriptcount, row_count, ('The seed data contains three '
                                                  'Script objects with the script_type'
                                                  'EX, which should appear in this table'))

        displayed_doc_count = self.browser.find_elements_by_xpath(
            '//*[@id="extraction_script_table"]/tbody/tr[2]/td[2]')[0].text

        model_doc_count = DataDocument.objects.filter(
            extractedtext__extraction_script=6).count()

        self.assertEqual(displayed_doc_count, str(model_doc_count),
                         ('The displayed number of datadocuments should match '
                          'the number whose related extracted text objects used '
                          ' the extraction script'))

        displayed_pct_checked = self.browser.find_elements_by_xpath(
            '//*[@id="extraction_script_table"]/tbody/tr[2]/td[3]')[0].text
        # this assumes that pk=6 will be a script_type of 'EX'
        model_pct_checked = Script.objects.get(pk=6).get_pct_checked()
        self.assertEqual(displayed_pct_checked, model_pct_checked,
                         ('The displayed percentage should match what is '
                          'derived from the model'))

        es = Script.objects.get(pk=6)

        print('method version: ----- ExtractedText objects in Script 6 ------')
        print(es.extractedtext_set.filter(
            qa_checked=True).values('prod_name', 'qa_checked'))

        self.assertEqual(es.get_qa_complete_extractedtext_count(), 1,
                         ('The ExtractionScript object should return 1 '
                          'qa_checked ExtractedText objects'))
        # Set qa_checked property to True for one of the ExtractedText objects
        self.assertEqual(ExtractedText.objects.get(pk=121647).qa_checked, False,
                         "The qa_checked value should be False before the change in the model")
        et_change = ExtractedText.objects.get(pk=121647)
        et_change.qa_checked = True
        et_change.save()
        self.assertEqual(ExtractedText.objects.get(pk=121647).qa_checked, True,
                         'The object should now have qa_checked = True')
        # This checks the other ExtractedText object
        self.assertEqual(ExtractedText.objects.get(pk=121627).qa_checked, True,
                         'The other object has always had qa_checked = True')

        es.refresh_from_db()
        self.assertEqual(es.get_qa_complete_extractedtext_count(), 2,
                         ('The ExtractionScript object should return 2 '
                          'qa_checked ExtractedText object'))

        self.assertEqual(2, es.get_qa_complete_extractedtext_count(),
                         'Check the numerator in the model layer')
        self.assertEqual(13, es.get_datadocument_count(),
                         'Check the denominator in the model layer')
        model_pct_checked = Script.objects.get(pk=6).get_pct_checked()
        self.assertEqual(model_pct_checked, "{0:.0f}%".format(2./13 * 100),
                         ('The get_pct_checked() method should return 2/13 as percentage'
                          ' from the model layer'))
        self.browser.refresh()

        displayed_pct_checked = self.browser.find_elements_by_xpath(
            '//*[@id="extraction_script_table"]/tbody/tr[2]/td[3]')[0].text

        self.assertEqual(displayed_pct_checked, model_pct_checked,
                         ('The displayed percentage in the browser layer should '
                          'reflect the newly checked extracted text object'))
        # A button for each row that will take you to the script's QA page
        # https://github.com/HumanExposure/factotum/issues/36
        script_qa_link = self.browser.find_element_by_xpath(
            '//*[@id="extraction_script_table"]/tbody/tr[contains(.,"Sun INDS (extract)")]/td[4]/a'
        )
        self.assertIn('extractionscript/6',
                      script_qa_link.get_attribute('outerHTML'))
        # Before clicking the link, the script's qa_begun property
        # should be false
        self.assertEqual(Script.objects.get(pk=6).qa_begun, False,
                         'The qa_done property of the Script should be False')

        script_qa_link.click()
        # The link should open a page where the h1 text matches the title

        # of the Script
        h1 = self.browser.find_element_by_xpath('/html/body/div/h1').text
        self.assertIn(Script.objects.get(pk=6).title, h1,
                      'The <h1> text should equal the .title of the Script')

        # Opening the ExtractionScript's QA page should set its qa_begun
        # property to True
        self.assertEqual(Script.objects.get(pk=6).qa_begun, True,
                         'The qa_done property of the ExtractionScript should now be True')
        # Go back to the QA index page to confirm
        self.browser.get('%s%s' % (self.live_server_url, '/qa'))
        script_qa_link = self.browser.find_element_by_xpath(
            '//*[@id="extraction_script_table"]/tbody/tr[contains(.,"Sun INDS (extract)")]/td[4]/a'
        )
        self.assertEqual(script_qa_link.text, 'Continue QA',
                         'The QA button should now say "Continue QA" instead of "Begin QA"')

        ### Testing the QA Group and Extracted Text-level views
        #
        # go to the QA Group page
        # find the row that contains the Sun INDS link, click the fourth td
        script_qa_link = self.browser.find_element_by_xpath(
            '//*[@id="extraction_script_table"]/tbody/tr[contains(.,"Sun INDS (extract)")]/td[4]/a'
        )
        dd_test = DataDocument.objects.filter(title__startswith="Alba Hawaiian Coconut Milk Body Cream")[0]
        pk_test = dd_test.id
        script_qa_link.click()
        # confirm that the QA Group index page has opened
        self.assertIn("/qa/extractionscript" , self.browser.current_url, \
            "The opened page should include the qa/extractionscript route")
        #
        # The record with the test_pk ID is no longer going to appear in this page,
        # because it has been set to qa_checked = True
        # pick an arbitrary first record instead
        ext_qa_link = self.browser.find_element_by_xpath(
            '//*[@id="extracted_text_table"]/tbody/tr[1]/td[6]/a')
        qa_url = ext_qa_link.get_attribute('href')
        qa_pk = qa_url.rsplit('/', 1)[-1]
        dd_test = DataDocument.objects.get(pk=qa_pk)

        ext_qa_link.click()

        # confirm that the pdf was also opened
        window_before = self.browser.window_handles[0]
        window_after = self.browser.window_handles[1]
        self.browser.switch_to_window(window_after)
        self.assertIn(dd_test.filename, self.browser.current_url,
                      "The opened page should include the pdf file name")
        self.browser.close()
        self.browser.switch_to_window(window_before)

        # TODO: add seed records that allow testing the Skip button
        btn_skip = self.browser.find_element_by_xpath(
            '/html/body/div[1]/div[2]/div/a[3]')

        # clicking the exit button should return the browser to the
        # QA Group page
        btn_exit = self.browser.find_element_by_xpath(
            '/html/body/div[1]/div[2]/div/a[4]')
        btn_exit.click()
        self.assertIn("/qa/extractionscript", self.browser.current_url,
                      "The opened page should include the qa/extractionscript route")

    def test_approval(self):
        testpk = 156051
        with transaction.atomic():
            et = ExtractedText.objects.get(pk=testpk)
            next_pk = et.next_extracted_text_in_qa_group()
            # the example document is Sun_INDS_89
            # start on the QA page
            self.browser.get('%s%s' % (self.live_server_url, '/qa'))
            # go to the Sun INDS script's page
            script_qa_link = self.browser.find_element_by_xpath(
                '//*[@id="extraction_script_table"]/tbody/tr[contains(.,"Sun INDS (extract)")]/td[4]/a'
            )
            script_qa_link.click()
            # Open the data document's page
            dd_qa_link = self.browser.find_element_by_xpath(
                '//*[@id="extracted_text_table"]/tbody/tr[contains(.,"Sun_INDS_89")]/td[6]/a'
            )
            dd_qa_link.click()
            # one of the open windows is the pdf, the other is the editing screen
            self.browser.switch_to_window(self.browser.window_handles[0])
            # print(self.browser.current_url)
            if 'media' in self.browser.current_url:
                print(self.browser.current_url)
                pdf_window = self.browser.window_handles[0]
                qa_window = self.browser.window_handles[1]
            else:
                pdf_window = self.browser.window_handles[1]
                qa_window = self.browser.window_handles[0]
            # close the pdf window
            self.browser.switch_to_window(pdf_window)
            self.browser.close()
            # Now in the QA window:
            self.browser.switch_to_window(qa_window)
            btn_approve = self.browser.find_element_by_xpath(
                '/html/body/div[1]/div[2]/div/a[1]')
            self.assertTrue(et.qa_checked == False,
                            "Before clicking, qa_checked should be False")
            btn_approve.click()
            # post-click
            #et = ExtractedText.objects.get(pk=testpk)
            # print(self.browser.current_url)
            self.assertTrue(
                et.qa_checked, "After clicking, qa_checked should be True")
            # the status and the user should have been updated
            self.assertEqual(ExtractedText.APPROVED_WITHOUT_ERROR, et.qa_status,
                             "qa_status should be Approved without errors")
            self.assertEqual("Karyn", et.qa_approved_by.username,
                             "The qa_approved_by user should be Karyn")

            self.assertIn(str(next_pk), self.browser.current_url,
                          "Now the current URL should include the original ExtractedText object's next id")

            transaction.set_rollback(True)
            # see if it has been rolled back
        print('\n Inside test method, after rollback')
        print(ExtractedText.objects.get(pk=testpk).qa_checked)

    def check_persistence_model(self):
        ds = DataSource.objects.filter(title='Walmart MSDS')[0]
        # start the transaction here
        atm = transaction.atomic()
        atm.__enter__()

        self.dg = self.create_data_group(data_source=ds)
        print('\nDataGroup object count after adding one:')
        print(DataGroup.objects.count())
        transaction.set_rollback(True)
        atm.__exit__(None, None, None)
        print('Rollback done')
        print('\nDataGroup object count after rollback:')
        print(DataGroup.objects.count())

    def check_persistence_ui(self):
        print('\nDataSource object count before adding:')
        print(DataSource.objects.count())
        # start the transaction here
        with transaction.atomic():
            self.browser.get('%s%s' %
                             (self.live_server_url, '/datasource/new'))
            self.browser.find_element_by_xpath(
                '//*[@id="id_title"]').send_keys('Test Data Source')
            select = Select(self.browser.find_element_by_id('id_type'))
            select.select_by_visible_text('msds')
            self.browser.find_element_by_xpath(
                '/html/body/div[1]/form/button').click()
            print('\nDataSource object count after adding one:')
            print(DataSource.objects.count())
            transaction.set_rollback(True)

        print('\nDataSource object count after rollback:')
        print(DataSource.objects.count())


class TestExtractedText(StaticLiveServerTestCase):

    fixtures = ['seed_data']

    def setUp(self):
        if settings.TEST_BROWSER == 'firefox':
            self.browser = webdriver.Firefox()
        else:
            self.browser = webdriver.Chrome()
        log_karyn_in(self)

    def tearDown(self):
        self.browser.quit()

    def test_submit_button(self):
        self.browser.get(self.live_server_url + '/datagroup/1')
        extract_text_form_button = self.browser.find_element_by_id(
            'btn_extract_text_form')
        extract_text_form_button.click()

        submit_button = self.browser.find_element_by_name('extract_button')
        self.assertEqual(submit_button.is_enabled(), False,
                         ("This button shouldn't be enabled until there "
                          "is a file selected in the file input."))
        file_input = self.browser.find_element_by_name('extract_file')
        file_input.send_keys(os.path.join(
            os.getcwd(), "sample_files", "test_extract.csv"))
        submit_button = self.browser.find_element_by_name('extract_button')
        # if this fails here, the file likely isn't in the repo anymore
        # or has been deleted
        self.assertEqual(submit_button.is_enabled(), True,
                         ("This button should be enabled now that there "
                          "is a file selected in the file input."))


def clean_label(self, label):
    """Remove the "remove" character used in select2."""
    return label.replace('\xd7', '')


def wait_for_element(self, elm, by='id', timeout=10):
    wait = WebDriverWait(self.browser, timeout)
    wait.until(EC.presence_of_element_located((By.XPATH, elm)))
    return self.browser.find_element_by_xpath(elm)
