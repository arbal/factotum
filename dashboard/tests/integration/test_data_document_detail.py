import time

from django.contrib.auth.models import User
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait, Select

from dashboard.models import DataDocument, ExtractedText, FunctionalUse, RawChem
from dashboard.tests.loader import fixtures_standard, load_browser


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

    def test_list_presence_keywords(self):
        """
        Test that a CP datadocument has a functioning keyword/tag input box, which uses the
        Select2 widget and AJAX to retrieve matching keywords from the server
        """
        doc = DataDocument.objects.get(pk=254781)
        wait = WebDriverWait(self.browser, 10)
        self.browser.get(self.live_server_url + doc.get_absolute_url())
        card = wait.until(
            ec.element_to_be_clickable(
                (By.ID, f"chem-click-{doc.extractedtext.rawchem.first().pk}")
            )
        )
        count_span = self.browser.find_element_by_id("selected")
        self.assertTrue(
            count_span.text == "0", "User should see number of selected cards."
        )
        tags = card.find_elements_by_class_name("tag-btn")
        # We should start with 2 tags for this document
        self.assertEqual(
            [t.text for t in tags],
            ["flavor", "slimicide"],
            "Tags should be labelled in card.",
        )
        save_button = self.browser.find_element_by_id("keyword-save")
        self.assertFalse(save_button.is_enabled())
        card.click()
        self.assertTrue(save_button.is_enabled())
        self.assertTrue(
            count_span.text == "1", "User should see number of selected cards."
        )

        input_el = self.browser.find_element_by_xpath(
            '//*[@id="id_tags"]/following-sibling::span[1]/descendant::input[1]'
        )
        input_el.send_keys("pesticide")
        wait.until(
            ec.text_to_be_present_in_element(
                (By.XPATH, "//*[@id='select2-id_tags-results']/li[1]"), "pesticide"
            )
        )
        option = self.browser.find_element_by_xpath(
            "//*[@id='select2-id_tags-results']/li[1]"
        )
        option.click()
        save_button.submit()
        card = wait.until(ec.presence_of_element_located((By.ID, "chem-click-759")))
        tags = card.find_elements_by_class_name("tag-btn")
        self.assertEqual(
            [t.text for t in tags],
            ["flavor", "pesticide", "slimicide"],
            "Tags should be labelled in card.",
        )

        # test delete all tags
        delete_tags_button = self.browser.find_element_by_id("delete-all-tags")
        self.assertIsNotNone(delete_tags_button, "should have a delete all tag button")
        delete_tags_button.click()
        model = wait.until(
            ec.presence_of_element_located((By.ID, "delete-all-tags-modal"))
        )
        confirm_btn = model.find_element_by_id("delete-all-tags-delete-btn")
        confirm_btn.submit()
        card = wait.until(ec.presence_of_element_located((By.ID, "chem-click-759")))
        tags = card.find_elements_by_class_name("tag-btn")
        self.assertEqual(0, len(tags), "Tags should be removed")

    def test_datadoc_add_extracted(self):
        """
        Test that when a datadocument has no ExtractedText, the user can add one in the browser
        """
        for doc_id in [155324, 254782]:  # [CO, CP] records with no ExtractedText
            # Verify this document has no Extracted Texts.
            self.assertEqual(
                0,
                ExtractedText.objects.filter(data_document_id=doc_id).count(),
                "This Data Document is already extracted",
            )

            # QA Page
            dd_url = self.live_server_url + f"/datadocument/{doc_id}/"
            self.browser.get(dd_url)
            # Activate the edit mode
            self.browser.find_element_by_xpath(
                '//*[@id="btn-add-or-edit-extracted-text"]'
            ).click()

            # Verify that the modal window appears by finding the Cancel button
            # The modal window does not immediately appear, so the browser
            # should wait for the button to be clickable
            wait = WebDriverWait(self.browser, 10)
            cancel_button = wait.until(
                ec.element_to_be_clickable(
                    (By.XPATH, "//*[@id='extracted-text-modal-cancel']")
                )
            )
            self.assertEqual(
                "Cancel", cancel_button.text, "The Cancel button should say Cancel"
            )
            cancel_button.click()
            # Verify that no ExtractedText record was created
            self.assertEqual(
                0,
                ExtractedText.objects.filter(data_document_id=doc_id).count(),
                "the count of ExtractedText records related to the \
                data document should be zero",
            )

            # Wait for the modal div to disappear
            wait.until(ec.invisibility_of_element((By.XPATH, '//*[@id="extextModal"]')))
            # Click the Add button again to reopen the editor
            add_button = self.browser.find_element_by_xpath(
                '//*[@id="btn-add-or-edit-extracted-text"]'
            )
            add_button.click()
            # Once again, check that the controls on the modal form are clickable
            # before trying to interact with them
            wait.until(
                ec.element_to_be_clickable(
                    (By.XPATH, "//*[@id='extracted-text-modal-cancel']")
                )
            )
            # Add a "Product Name" for CO documents and verify
            if doc_id == 155324:
                prod_name_box = self.browser.find_element_by_id("id_prod_name")
                # Add a prod_name value to the box
                prod_name_box.send_keys("Fake Product")
                save_button = self.browser.find_element_by_id(
                    "extracted-text-modal-save"
                )
                save_button.click()
                wait.until(
                    ec.text_to_be_present_in_element(
                        (By.XPATH, "//*[@id='id_prod_name']"), "Fake Product"
                    )
                )
                self.assertEqual(
                    self.browser.find_element_by_id("id_prod_name").text, "Fake Product"
                )
                # Confirm the presence of the new ExtractedText record
                et = ExtractedText.objects.get(data_document_id=doc_id)
                self.assertEqual(
                    "Fake Product",
                    et.prod_name,
                    "The prod_name of the new object should match what was entered",
                )
                self.assertEqual(
                    User.objects.filter(username="Karyn").first(),
                    et.updated_by,
                    "System should show that Karyn updated this record",
                )

            # Add a "Document Date" for CP documents and verify
            elif doc_id == 254782:
                prod_name_box = self.browser.find_element_by_id("id_doc_date")
                # Add a prod_name value to the box
                prod_name_box.send_keys("2018")
                save_button = self.browser.find_element_by_id(
                    "extracted-text-modal-save"
                )
                save_button.click()
                wait.until(
                    ec.text_to_be_present_in_element(
                        (By.XPATH, "//*[@id='id_doc_date']"), "2018"
                    )
                )
                self.assertEqual(
                    self.browser.find_element_by_id("id_doc_date").text, "2018"
                )
                # Confirm the presence of the new ExtractedText record
                et = ExtractedText.objects.get(data_document_id=doc_id)
                self.assertEqual(
                    "2018",
                    et.doc_date,
                    "The prod_name of the new object should match what was entered",
                )
                self.assertEqual(
                    User.objects.filter(username="Karyn").first(),
                    et.updated_by,
                    "System should show that Karyn updated this record",
                )

    def test_sd_group_type(self):
        """A Composition data group should display links to
        both the data document detail page and the pdf file.
        A Supplemental data group should only display links
        to the stored pdf files in the /media/ folder """

        # First check 'CO' link first to see if one exists
        dg_pk = 30
        list_url = self.live_server_url + f"/datagroup/{dg_pk}/"
        self.browser.get(list_url)

        # The link to the pdf should exist
        try:
            pdf_link = WebDriverWait(self.browser, 5).until(
                ec.visibility_of_element_located(
                    (By.XPATH, '//*[@id="docs"]/tbody/tr/td[1]/a')
                )
            )
        except NoSuchElementException:
            self.fail("PDF icon should exist, but does not.")

        # The title of the data document detail page
        # should have a hyperlink
        try:
            self.browser.find_element_by_xpath('//a[@href="/datadocument/179486/"]')
        except NoSuchElementException:
            self.fail("Hyperlink for CO title does not exist.")

        # Now check 'SU' link first to see if one exists
        dg_pk = 53
        list_url = self.live_server_url + f"/datagroup/{dg_pk}/"
        self.browser.get(list_url)

        # The link to the pdf should exist
        try:
            pdf_link = WebDriverWait(self.browser, 5).until(
                ec.visibility_of_element_located(
                    (By.XPATH, '//*[@id="docs"]/tbody/tr/td[1]/a')
                )
            )
        except NoSuchElementException:
            self.fail("PDF icon should exist, but does not.")

        # The title of the data document detail page
        # should not have a hyperlink
        try:
            self.browser.find_element_by_xpath('//td[text()="Supplemental Memo"]')
        except NoSuchElementException:
            self.fail("Label for SU title does not exist.")

    def test_co_clean_comp_slider(self):
        dd_pk = 156051
        list_url = self.live_server_url + f"/datadocument/{dd_pk}/"
        self.browser.get(list_url)
        time.sleep(1)
        # Verify that the sliders have been generated for extracted chemicals in this datadocument
        try:
            slider = WebDriverWait(self.browser, 10).until(
                ec.visibility_of_element_located((By.XPATH, '//*[@id="slider856"]'))
            )
            slider2 = WebDriverWait(self.browser, 10).until(
                ec.visibility_of_element_located((By.XPATH, '//*[@id="slider2"]'))
            )
        except (NoSuchElementException, TimeoutException):
            self.fail("Sliders should exist on this page, but does not.")

    def test_chemical_update(self):
        docs = DataDocument.objects.filter(pk__in=[156051, 354786])
        for doc in docs:
            wait = WebDriverWait(self.browser, 10)

            list_url = self.live_server_url + f"/datadocument/{doc.pk}/"
            self.browser.get(list_url)
            chem = doc.extractedtext.rawchem.first()
            chem_pk = chem.pk

            wait.until(
                ec.element_to_be_clickable(
                    (By.XPATH, f'//*[@id="chemical-update-{chem.pk}"]')
                )
            ).click()

            # Verify that the modal window appears by finding the Save button
            # The modal window does not immediately appear, so the browser
            # should wait for the button to be clickable
            save_button = wait.until(
                ec.element_to_be_clickable((By.XPATH, "//*[@id='saveChem']"))
            )

            report_funcuse_box = wait.until(
                ec.element_to_be_clickable(
                    (By.XPATH, f"//*[@id='id_functional_uses-0-report_funcuse']")
                )
            )
            report_funcuse_box.send_keys("canoeing")

            self.assertEqual("Save changes", save_button.get_attribute("value"))
            save_button.click()
            self.browser.refresh()

            audit_link = wait.until(
                ec.element_to_be_clickable(
                    (By.XPATH, f"//*[@id='chemical-audit-log-{chem_pk}']")
                )
            )

            self.assertIn("Last updated: 0 minutes ago", audit_link.text)

            # audit_link.click() does not work in chromedriver here for some reason
            self.browser.execute_script("arguments[0].click();", audit_link)

            datatable = wait.until(
                ec.visibility_of_element_located((By.XPATH, "//*[@id='audit-log']"))
            )
            self.assertIn("canoeing", datatable.text)

    def test_multiple_fu(self):
        docs = DataDocument.objects.filter(pk__in=[5])
        for doc in docs:
            list_url = self.live_server_url + f"/datadocument/{doc.pk}/"
            self.browser.get(list_url)
            chem = doc.extractedtext.rawchem.first()
            chem_pk = chem.pk

            functional_uses_col = self.browser.find_element_by_xpath(
                f'//*[@id="functional_uses_{chem_pk}"]'
            )

            self.browser.find_element_by_xpath(
                f'//*[@id="chemical-update-{chem.pk}"]'
            ).click()

            # Verify that the modal window appears by finding the Save button
            # The modal window does not immediately appear, so the browser
            # should wait for the button to be clickable
            wait = WebDriverWait(self.browser, 10)
            save_button = wait.until(
                ec.element_to_be_clickable((By.XPATH, "//*[@id='saveChem']"))
            )

            funcuse_add_btn = self.browser.find_element_by_xpath(
                f'//*[@id="funcuse-add"]'
            )
            funcuse_add_btn.click()
            new_funcuse_box = wait.until(
                ec.element_to_be_clickable(
                    (By.XPATH, f"//*[@id='id_functional_uses-1-report_funcuse']")
                )
            )
            new_funcuse_box.send_keys("adhesive")
            save_button.click()

            # Reload the page after saving
            self.browser.get(list_url)

            self.assertEqual(
                FunctionalUse.objects.filter(chem_id=chem_pk)
                .filter(report_funcuse="adhesive")
                .count(),
                1,
            )

            functional_uses_col = wait.until(
                ec.presence_of_element_located(
                    (By.XPATH, f'//*[@id="functional_uses_{chem_pk}"]')
                )
            )
            self.assertIn("surfactant", functional_uses_col.text)

    def test_lm_chemical_update(self):
        wait = WebDriverWait(self.browser, 10)
        doc = DataDocument.objects.get(pk=9)
        self.browser.get(self.live_server_url + f"/datadocument/{doc.pk}/")

        # LM datadocuments shouldn't be able to have products associated with them
        with self.assertRaises(NoSuchElementException):
            self.browser.find_element_by_id("add_product_button")

        self.browser.find_element_by_xpath(
            '//*[@id="btn-add-or-edit-extracted-text"]'
        ).click()
        save_button = wait.until(
            ec.element_to_be_clickable(
                (By.XPATH, "//*[@id='extracted-text-modal-save']")
            )
        )
        Select(self.browser.find_element_by_id("id_study_type")).select_by_visible_text(
            "Non-targeted or Suspect Screening"
        )
        self.browser.find_element_by_id("id_pmid").send_keys("01234567890123456789")
        self.browser.find_element_by_id("id_media").send_keys("Lorem ipso fido leash")
        save_button.click()

        # Saving the form triggers a refresh.  Wait until the old save button has become stale before proceeding.
        wait.until(ec.staleness_of(save_button))
        study_type = wait.until(
            ec.visibility_of_element_located((By.ID, "id_study_type"))
        )
        self.assertIn("Non-targeted or Suspect Screening", study_type.text)

        add_chem_button = wait.until(
            ec.element_to_be_clickable((By.XPATH, "//*[@id='add_chemical']"))
        )
        add_chem_button.click()

        save_button = wait.until(ec.element_to_be_clickable((By.ID, "saveChem")))

        self.assertTrue(len(self.browser.find_elements_by_id("id_raw_chem_name")) > 0)
        self.assertTrue(len(self.browser.find_elements_by_id("id_raw_cas")) > 0)
        self.assertFalse(len(self.browser.find_elements_by_id("id_raw_min_comp")) > 0)
        self.assertFalse(
            len(self.browser.find_elements_by_id("id_raw_central_comp")) > 0
        )
        self.assertFalse(len(self.browser.find_elements_by_id("id_raw_max_comp")) > 0)
        self.assertFalse(len(self.browser.find_elements_by_id("id_unit_type")) > 0)
        self.assertFalse(
            len(self.browser.find_elements_by_id("id_ingredient_rank")) > 0
        )
        self.assertFalse(
            len(self.browser.find_elements_by_id("id_weight_fraction_type")) > 0
        )
        self.assertFalse(len(self.browser.find_elements_by_id("id_component")) > 0)

        self.browser.find_element_by_id("id_raw_chem_name").send_keys(
            "The Rawest Chem Name"
        )

        save_button.click()

        time.sleep(3)
        raw_chem = RawChem.objects.filter(extracted_text_id=doc.pk).first()

        self.assertEqual(raw_chem.updated_by, User.objects.get(username="Karyn"))
        self.assertTrue(raw_chem.updated_at != "")

        self.assertInHTML(
            "The Rawest Chem Name",
            self.browser.find_element_by_id(f"raw_chem_name-{raw_chem.pk}").text,
        )

    def test_co_multiple_fu(self):
        doc = DataDocument.objects.get(pk=7)

        list_url = self.live_server_url + f"/datadocument/{doc.pk}/"
        self.browser.get(list_url)
        chem = doc.extractedtext.rawchem.first()

        self.browser.find_element_by_xpath(
            f'//*[@id="chemical-update-{chem.pk}"]'
        ).click()

        # Verify that the modal window appears by finding the Save button
        # The modal window does not immediately appear, so the browser
        # should wait for the button to be clickable
        wait = WebDriverWait(self.browser, 10)
        save_button = wait.until(
            ec.element_to_be_clickable((By.XPATH, "//*[@id='saveChem']"))
        )

        # verify that Add Functional Use button exists
        funcuse_add_btn = self.browser.find_element_by_xpath(f'//*[@id="funcuse-add"]')
        funcuse_add_btn.click()
        new_funcuse_box = wait.until(
            ec.element_to_be_clickable(
                (By.XPATH, f"//*[@id='id_functional_uses-1-report_funcuse']")
            )
        )
        new_funcuse_box.send_keys("adhesive")
        save_button.click()

        # Reload the page after saving
        self.browser.get(list_url)

        new_fu = (
            FunctionalUse.objects.filter(chem_id=chem.pk)
            .filter(report_funcuse="adhesive")
            .first()
        )

        self.assertIsNotNone(new_fu)
        time.sleep(1)
        functional_uses_col = self.browser.find_element_by_xpath(
            f'//*[@id="functional_uses_{new_fu.id}"]'
        )
        self.assertIn("adhesive", functional_uses_col.text)

    def test_cp_multiple_fu(self):
        doc = DataDocument.objects.get(pk=354787)

        list_url = self.live_server_url + f"/datadocument/{doc.pk}/"
        self.browser.get(list_url)
        chem = doc.extractedtext.rawchem.first()

        self.browser.find_element_by_xpath(
            f'//*[@id="chemical-update-{chem.pk}"]'
        ).click()

        # Verify that the modal window appears by finding the Save button
        # The modal window does not immediately appear, so the browser
        # should wait for the button to be clickable
        wait = WebDriverWait(self.browser, 10)
        save_button = wait.until(
            ec.element_to_be_clickable((By.XPATH, "//*[@id='saveChem']"))
        )

        # verify that Add Functional Use button exists
        funcuse_add_btn = self.browser.find_element_by_xpath(f'//*[@id="funcuse-add"]')
        funcuse_add_btn.click()
        new_funcuse_box = wait.until(
            ec.element_to_be_clickable(
                (By.XPATH, f"//*[@id='id_functional_uses-1-report_funcuse']")
            )
        )
        new_funcuse_box.send_keys("adhesive")
        save_button.click()

        # Reload the page after saving
        self.browser.get(list_url)

        new_fu = (
            FunctionalUse.objects.filter(chem_id=chem.pk)
            .filter(report_funcuse="adhesive")
            .first()
        )

        self.assertIsNotNone(new_fu)

        functional_uses_col = self.browser.find_element_by_xpath(
            f'//*[@id="functional_uses_{new_fu.id}"]'
        )
        self.assertIn("adhesive", functional_uses_col.text)
