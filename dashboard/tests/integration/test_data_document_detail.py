from dashboard.tests.loader import *
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from dashboard.models import *
from django.urls import reverse

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
        self.browser = load_browser()
        log_karyn_in(self)

    def tearDown(self):
        self.browser.quit()

    def test_list_presence_keywords(self):
        '''
        Test that a CP datadocument has a functioning keyword/tag input box, which uses the
        Select2 widget and AJAX to retrieve matching keywords from the server
        '''
        doc = DataDocument.objects.get(pk=254781)
        wait = WebDriverWait(self.browser, 10)
        self.browser.get(self.live_server_url + reverse('data_document', kwargs={'pk': doc.pk}))
        # We should start with 2 tags for this document
        tags = self.browser.find_element_by_xpath('//*[@id="id_tags"][count(option) = 2]')
        self.assertTrue(tags,
                        'Listpresence records for this doc should begin with 2 associated keywords')
        input_el = self.browser.find_element_by_xpath('//*[@id="id_tags"]/following-sibling::span[1]/descendant::input[1]')
        input_el.send_keys('pesticide')
        wait.until(
            ec.text_to_be_present_in_element(
                    (By.XPATH, "//*[@id='select2-id_tags-results']/li[1]"),
                    "pesticide")
            ) 
        option = self.browser.find_element_by_xpath("//*[@id='select2-id_tags-results']/li[1]")
        option.click()
        btn_save = self.browser.find_element_by_xpath('//*[@id="cards"]/div[1]/form/button')
        btn_save.click()
        # Check in the ORM to see if the keyword has been associated with
        # the ExtractedListPresence records
        elp_id = RawChem.objects.filter(extracted_text_id=254781).first().id
        elp_keyword_count = ExtractedListPresenceToTag.objects.filter(content_object_id = elp_id).count()
        self.assertEqual(elp_keyword_count , 3)
        tags = self.browser.find_element_by_xpath('//*[@id="id_tags"][count(option) = 3]')
        self.assertTrue(tags,
                        'Listpresence records for this doc should now have 3 associated keywords')

    def test_datadoc_add_extracted(self):
        '''
        Test that when a datadocument has no ExtractedText, the user can add one in the browser
        '''
        for doc_id in [155324   # CO record with no ExtractedText
                       ]:
            # QA Page
            dd_url = self.live_server_url + f'/datadocument/{doc_id}/'
            self.browser.get(dd_url)
            # Activate the edit mode
            self.browser.find_element_by_xpath(
                '//*[@id="btn-add-or-edit-extracted-text"]').click()

            # Verify that the modal window appears by finding the Cancel button
            # The modal window does not immediately appear, so the browser
            # should wait for the button to be clickable
            wait = WebDriverWait(self.browser, 10)
            cancel_button = wait.until(
                ec.element_to_be_clickable(
                    (By.XPATH, "//*[@id='extracted-text-modal-cancel']")
                )
            )
            self.assertEqual("Cancel", cancel_button.text,
                             'The Cancel button should say Cancel')
            cancel_button.click()
            # Verify that no ExtractedText record was created
            self.assertEqual(0, ExtractedText.objects.filter(
                data_document_id=doc_id).count(),
                "the count of ExtractedText records related to the \
                data document should be zero")

            # Wait for the modal div to disappear
            edit_modal = wait.until(
                ec.invisibility_of_element(
                    (By.XPATH, '//*[@id="extextModal"]')
                )
            )
            # Click the Add button again to reopen the editor
            add_button = self.browser.find_element_by_xpath(
                '//*[@id="btn-add-or-edit-extracted-text"]')
            add_button.click()
            # Once again, check that the controls on the modal form are clickable
            # before trying to interact with them
            cancel_button = wait.until(
                ec.element_to_be_clickable(
                    (By.XPATH, "//*[@id='extracted-text-modal-cancel']")
                )
            )
            prod_name_box = self.browser.find_element_by_id(
                'id_prod_name')
            # Add a prod_name value to the box
            prod_name_box.send_keys('Fake Product')
            save_button = self.browser.find_element_by_id(
                'extracted-text-modal-save')
            save_button.click()
            # Confirm the presence of the new ExtractedText record
            et = ExtractedText.objects.get(data_document_id=doc_id)
            self.assertEqual('Fake Product', et.prod_name,
                             "The prod_name of the new object should match what was entered")


