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
from django.utils import timezone
from django.test import LiveServerTestCase, override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from dashboard.models import (DataGroup, DataSource, DataDocument,
                              Script, ExtractedText, Product, PUC, ProductDocument, QAGroup)

from haystack import connections
from haystack.query import SearchQuerySet
from django.core.management import call_command
from haystack.management.commands import update_index, rebuild_index


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


class TestDataSourceAndDataGroup(StaticLiveServerTestCase):

    fixtures = [ '00_superuser.yaml', '01_lookups.yaml',
            '02_datasource.yaml', '03_datagroup.yaml', '04_productcategory.yaml',
            '05_product.yaml', '06_datadocument.yaml' , '07_script.yaml',
            '08_extractedtext.yaml','09_productdocument.yaml']

    def setUp(self):
        self.browser = webdriver.Chrome()
        log_karyn_in(self)

    def tearDown(self):
        self.browser.quit()

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
        wrap_div = self.browser.find_element_by_class_name('dataTables_wrapper')
        self.assertIn("Show", wrap_div.text, 'DataTables missing...')

    # Data Groups

    def test_data_group_name(self):
        dgpk = DataGroup.objects.filter(name='Walmart MSDS 1')[0].pk
        self.browser.get(self.live_server_url + '/datagroup/' + str(dgpk))
        h1 = self.browser.find_element_by_name('title')
        self.assertIn('Walmart MSDS 1', h1.text)
        # Checking the URL by row is too brittle
        #pdflink = self.browser.find_elements_by_xpath(
        #    '//*[@id="d-docs"]/tbody/tr[2]/td[1]/a')[0]
        #self.assertIn('shampoo.pdf', pdflink.get_attribute('href'))
        rows = self.browser.find_elements_by_xpath(
                                        "//table[@id='registered']/tbody/tr")
        docs = DataDocument.objects.filter(data_group=dgpk)
        self.assertEqual(len(rows),len(docs),'This table needs to be the entire set of data documents for the group for downloading CSV.')

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

    def create_data_documents(self, data_group, data_source):
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
                                                 data_group=data_group)
                dds.append(dd)
            return dds

    # creation of another DataGroup from csv and pdf sources
    def test_new_data_group(self):
        # DataGroup, created using the model layer
        dg_count_before = DataGroup.objects.count()
        ds = DataSource.objects.filter(title='Walmart MSDS')[0]
        self.dg = self.create_data_group(data_source=ds)
        dg_count_after = DataGroup.objects.count()
        self.assertEqual(dg_count_after, dg_count_before + 1,
                         "Confirm the DataGroup object has been created")
        new_dg_pk = self.dg.pk
        self.pdfs = self.upload_pdfs()
        self.dds = self.create_data_documents(self.dg, ds)

        # Use the browser layer to confirm that the object has been created
        self.browser.get('%s%s%s' % (self.live_server_url, '/datagroup/', new_dg_pk))
        self.assertEqual('factotum', self.browser.title,
                         "Testing open of show page for new data group")

        self.browser.get(self.live_server_url + reverse('data_group_detail',
                                                        kwargs={'pk': self.dg.pk}))
        self.assertEqual('factotum', self.browser.title)
        h1 = self.browser.find_element_by_name('title')
        self.assertIn('Walmart MSDS ', h1.text)

        # Use the browser layer to delete the DataGroup object
        # deleting the DataGroup should clean up the file system
        self.browser.get('%s%s%s' % (self.live_server_url, '/datagroup/delete/', new_dg_pk))
        del_button = self.browser.find_elements_by_xpath(('/html/body/div/form/'
                                                          'input[2]'))[0]
        del_button.click()
        self.assertEqual(DataGroup.objects.count(), dg_count_before,
                         "Confirm the DataGroup object has been deleted")

    def test_pagination(self):
        # The data group detail page uses server-side pagination to display the
        # related data documents
        dgpk = DataGroup.objects.get(name='Walmart MSDS 2').id
        self.browser.get('%s%s%s' % (self.live_server_url, '/datagroup/', str(dgpk)))
        pagebox = self.browser.find_element_by_xpath("/html/body/div[1]/nav/ul/li[1]/span")
        self.assertIn('Page 1', pagebox.text,
                         "Confirm the current page navigation box displays 'Page 1 of [some number]'")
        nextbox = self.browser.find_element_by_xpath('/html/body/div[1]/nav/ul/li[2]/a')
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
        self.browser.get(self.live_server_url + '/link_product_list/' + str(dgpk))
        create_prod_link = self.browser.find_element_by_xpath('//*[@id="products"]/tbody/tr[1]/td[2]/a')
        create_prod_link.click()

        title_input = self.browser.find_element_by_xpath('//*[@id="id_title"]')
        manufacturer_input = self.browser.find_element_by_xpath('//*[@id="id_manufacturer"]')
        brand_name_input = self.browser.find_element_by_xpath('//*[@id="id_brand_name"]')

        title_input.send_keys('A Product Title')
        manufacturer_input.send_keys('A Product Manufacturer')
        brand_name_input.send_keys('A Product Brand Name')
        # get the data document's ID from the URL, for later use
        dd_pk = re.search('(?P<pk>\d+)$', self.browser.current_url ).group(0)

        save_button = self.browser.find_element_by_xpath('/html/body/div[1]/form/button')
        save_button.click()
        # Saving the product should return the browser to the list of documents without products
        self.assertIn("link_product_list", self.browser.current_url)
        # The URL of the link_product_list page should be keyed to the DataGroup, not DataSource
        self.assertEqual(self.live_server_url + '/link_product_list/' + str(dgpk), self.browser.current_url)

        #check at the model level to confirm that the edits have been applied
        # self.assertEqual(dd_pk, 'x')
        pd = ProductDocument.objects.get(document=dd_pk)
        p = Product.objects.get(pk=pd.product.id)
        self.assertEqual('A Product Title', p.title)




    def test_PUC_assignment(self):
        self.browser.get(self.live_server_url + '/product_curation/')
        src_title = self.browser.find_elements_by_xpath(
            '//*[@id="products"]/tbody/tr[3]/td[1]/a')[0]
        ds = DataSource.objects.get(title=src_title.text)
        self.assertEqual(ds.title, 'Home Depot - ICF', 'Check the title of the group')
        puc_link = self.browser.find_elements_by_xpath(
            '//*[@id="products"]/tbody/tr[3]/td[4]')[0]
        products_missing_PUC = str(
            len(ds.source.filter(prod_cat__isnull=True)))
        self.assertEqual(puc_link.text, products_missing_PUC, ('The Assign PUC '
                                                               'link should display # of Products without a PUC'))

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
        self.browser.get('%s%s%s' % (self.live_server_url, '/product_puc/', str(ppk)))
        h2 = self.browser.find_element_by_xpath('/html/body/div/h2').text
        self.assertIn(h2, Product.objects.get(pk=ppk).title ,
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
        self.browser.get('%s%s%s' % (self.live_server_url, '/product/',ppk))
        puc_after = self.browser.find_element_by_id('prod_cat')
        self.assertNotEqual(puc_before, puc_after,
                            "The object's prod_cat should have changed")
        # Confirm that the puc_assigned_usr has been set to the current user
        puc_assigned_usr_after = self.browser.find_element_by_id('puc_assigned_usr').text
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
        self.browser.get('%s%s%s' % (self.live_server_url, '/product_puc/',ppk))
        cancel_a = self.browser.find_element_by_xpath('/html/body/div/div/form/a')
        # find out the path that the Cancel button will use
        cancel_a_href = cancel_a.get_attribute("href")
        # open that page
        self.browser.get(cancel_a_href)
        # make sure it shows a DataSource
        h2 = self.browser.find_element_by_xpath('/html/body/div/div[1]/h2').text
        self.assertIn(ds.title, h2,
                      'The <h2> text should equal the .title of the DataSource')


class TestQAScoreboard(StaticLiveServerTestCase):
    # Issue 35 https://github.com/HumanExposure/factotum/issues/35
    # Definition of Done:
    # A QA Home Page
    # A link in the nav bar to the QA Home page
    # A Table on the QA Home page
    # A button for each row in the table that will take you to #36 (Not Implemented Yet)
    fixtures = [ '00_superuser.yaml', '01_lookups.yaml',
            '02_datasource.yaml', '03_datagroup.yaml', '04_productcategory.yaml',
            '05_product.yaml', '06_datadocument.yaml' , '07_script.yaml', '08_extractedtext.yaml']

    def setUp(self):
        self.browser = webdriver.Chrome()
        log_karyn_in(self)

    def tearDown(self):
        self.browser.quit()

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
        model_pct_checked = Script.objects.get(pk=6).get_pct_checked()
        self.assertEqual(displayed_pct_checked, model_pct_checked,
                         ('The displayed percentage should match what is '
                          'derived from the model'))

        es = Script.objects.get(pk=6)
        self.assertEqual(es.get_qa_complete_extractedtext_count(), 1,
                         ('The ExtractionScript object should return 1'
                          'qa_checked ExtractedText objects'))
        self.assertEqual(model_pct_checked, '8%')
        # Set qa_checked property to True for one of the ExtractedText objects
        # what are we testing in the 5 lines below?  rick
        self.assertEqual(ExtractedText.objects.get(pk=121647).qa_checked, False)
        et_change = ExtractedText.objects.get(pk=121647)
        et_change.qa_checked = True
        et_change.save()
        self.assertEqual(ExtractedText.objects.get(pk=121647).qa_checked, True,
                         'The object should now have qa_checked = True')

        es = Script.objects.get(pk=6)
        self.assertEqual(es.get_qa_complete_extractedtext_count(), 2,
                         ('The ExtractionScript object should return 2 '
                          'qa_checked ExtractedText objects'))

        self.assertEqual(2, es.get_qa_complete_extractedtext_count(),
                         'Check the numerator in the model layer')
        self.assertEqual(13, es.get_datadocument_count(),
                         'Check the denominator in the model layer')
        model_pct_checked = Script.objects.get(pk=6).get_pct_checked()
        self.assertEqual(model_pct_checked, '15%',
                         ('The get_pct_checked() method should return 50 pct'
                          ' from the model layer'))
        self.browser.refresh()

        displayed_pct_checked = self.browser.find_elements_by_xpath(
            '//*[@id="extraction_script_table"]/tbody/tr[2]/td[3]')[0].text

        self.assertEqual(displayed_pct_checked, model_pct_checked,
                         ('The displayed percentage in the browser layer should '
                          'reflect the newly checked extracted text object'))
        # Create a new QAGroup and check that the only ext_texts displayed are
        # the one's assigned to the group
        script_qa_link = self.browser.find_element_by_xpath(
            '//*[@id="extraction_script_table"]/tbody/tr[contains(.,"Sun INDS (extract)")]/td[4]/a'
        )
        script_pk = int(script_qa_link.get_attribute('href').split('/')[-1])
        script = Script.objects.get(pk=script_pk)
        # Before clicking the link, the script's qa_done property
        # should be false
        self.assertEqual(Script.objects.get(pk=6).qa_begun, False,
                         'The qa_done property of the Script should be False')

        script_qa_link.click()
        # this QAGroup will not exist before click
        group = QAGroup.objects.get(extraction_script_id=script_pk)
        texts = ExtractedText.objects.filter(qa_group=group,qa_checked=False)
        # this is added because DataTables displays 10 rows by default
        t_len = len(texts) if len(texts)<=10 else 10
        row_count = len(self.browser.find_elements_by_xpath(
            "//table[@id='extracted_text_table']/tbody/tr"))
        self.assertEqual(row_count, t_len,
                         'The extractionscript view should only ExtractedTexts that are in the QAGroup and qa_checked is False')
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
        script_qa_link.click()
        # confirm that the QA Group index page has opened
        self.assertIn("/qa/extractionscript" , self.browser.current_url, \
            "The opened page should include the qa/extractionscript route")
        dd_name = self.browser.find_element_by_xpath('//*[@id="extracted_text_table"]/tbody/tr/td[3]').text
        #print(dd_name)
        dd_test = DataDocument.objects.filter(title__startswith=dd_name)[0]
        pk_test = dd_test.id
        ext_qa_link = self.browser.find_element_by_xpath('//*[@id="extracted_text_table"]/tbody/tr/td[6]/a')
        ext_qa_link.click()

        self.assertIn(str(pk_test) , self.browser.current_url, \
            "The opened page should include the pk of the data document")
        # confirm that the pdf was also opened
        window_before = self.browser.window_handles[0]
        window_after = self.browser.window_handles[1]
        self.browser.switch_to_window(window_after)
        self.assertIn(dd_test.filename, self.browser.current_url, \
            "The opened page should include the pdf file name")
        self.browser.close()
        self.browser.switch_to_window(window_before)

        # TODO: add seed records that allow testing the Skip button
        # time.sleep(120)
        # btn_skip = self.browser.find_element_by_xpath('/html/body/div[1]/div[2]/div/a[3]')
        # print(btn_skip.text)

        # clicking the exit button should return the browser to the
        # QA Group page
        btn_exit = self.browser.find_element_by_xpath('/html/body/div[1]/div[2]/div/a[4]')
        btn_exit.click()
        self.assertIn("/qa/extractionscript" , self.browser.current_url, \
                "The opened page should include the qa/extractionscript route")






def clean_label(self, label):
    """Remove the "remove" character used in select2."""
    return label.replace('\xd7', '')


def wait_for_element(self, elm, by='id', timeout=10):
    wait = WebDriverWait(self.browser, timeout)
    wait.until(EC.presence_of_element_located((By.XPATH, elm)))
    return self.browser.find_element_by_xpath(elm)



class TestFacetedSearch(StaticLiveServerTestCase):
    # Issue 104 https://github.com/HumanExposure/factotum/issues/104
    #
    fixtures = [ '00_superuser.yaml', '01_lookups.yaml',
            '02_datasource.yaml', '03_datagroup.yaml', '04_productcategory.yaml',
            '05_product.yaml', '06_datadocument.yaml' , '07_script.yaml', '09_productdocument.yaml']

    def setUp(self):
        self.browser = webdriver.Chrome()
        log_karyn_in(self)
        update_index.Command().handle(using=['default'])


    def tearDown(self):
        self.browser.quit()

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

        # Temporary fix: assign a PUC to the product, then rebuild the index

        p1 = Product.objects.get(pk=22)
        pc252 = ProductCategory.objects.get(pk=252)
        p1.prod_cat = pc252
        p1.save()
        # update the search engine index
        update_index.Command().handle(using=['default'])

        # Check for the elasticsearch engine
        self.browser.get('http://127.0.0.1:9200/')
        self.assertIn("9200", self.browser.current_url)
        self.assertIn("elasticsearch", self.browser.page_source,
                      "The search engine's server needs to be running")
        # if a Product object has a PUC assigned, that PUC should appear in the facet index
        sqs = SearchQuerySet().using('default').facet('prod_cat')
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


class TestExtractedText(StaticLiveServerTestCase):

    fixtures = ['seed_data']

    def setUp(self):
        self.browser = webdriver.Chrome()
        log_karyn_in(self)

    def tearDown(self):
        self.browser.quit()

    def test_submit_button(self):
        self.browser.get(self.live_server_url + '/datagroup/1')
        submit_button = self.browser.find_element_by_name('extract_button')
        self.assertEqual(submit_button.is_enabled(),False,
                         ("This button shouldn't be enabled until there "
                         "is a file selected in the file input."))
        file_input = self.browser.find_element_by_name('extract_file')
        file_input.send_keys(os.path.join(os.getcwd(),"sample_files","test_extract.csv"))
        submit_button = self.browser.find_element_by_name('extract_button')
        # if this fails here, the file likely isn't in the repo anymore
        # or has been deleted
        self.assertEqual(submit_button.is_enabled(),True,
                         ("This button should be enabled now that there "
                         "is a file selected in the file input."))

class TestAPI(StaticLiveServerTestCase):

    fixtures = ['00_superuser.yaml', '01_lookups.yaml',
            '02_datasource.yaml', '03_datagroup.yaml','04_productcategory.yaml',
            '05_product.yaml', '06_datadocument.yaml' , '07_script.yaml',
            '08_extractedtext.yaml','09_productdocument.yaml',
            '10_extractedchemical.yaml', '11_dsstoxsubstance.yaml' ]

    def setUp(self):
        self.browser = webdriver.Firefox()
        log_karyn_in(self)

    def tearDown(self):
        self.browser.quit()

    def test_JSON(self):
        sid = 'DTXSID6026296'
        self.browser.get(self.live_server_url + '/api/' + sid)
        if 'chrome' in str(type(self.browser)):
            pre = self.browser.find_element_by_tag_name("pre").text
        if 'firefox' in str(type(self.browser)):
            time.sleep(10)
            data_tab = self.browser.find_element_by_id('tab-1')
            data_tab.click()
            pre = self.browser.find_element_by_xpath('//div/pre').text
        api_out = json.loads(pre) # this would error if not JSON too!
        # print(api_out)
        self.assertEqual(type(api_out[0]),type(dict()),
                         ("This should be JSON"))
        self.assertIn("upc", api_out[0].keys(),
                      'A Product should contain a "upc" code.')
