from dashboard.tests.loader import load_browser, load_model_objects
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from dashboard.models import (
    DataSource,
    DataGroup,
    PUCToTag,
    ProductToPUC,
    ProductToPucClassificationMethod,
)
from django.test import tag
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait


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


@tag("loader")
class TestIntegration(StaticLiveServerTestCase):
    def setUp(self):
        self.objects = load_model_objects()
        self.browser = load_browser()
        log_karyn_in(self)

    def tearDown(self):
        self.browser.quit()

    def test_hem(self):
        for i in range(27):
            ds = DataSource.objects.create(title=f"Test_DS_{i}")
        list_url = self.live_server_url + "/datasources/"
        self.browser.get(list_url)
        row_count = len(
            self.browser.find_elements_by_xpath("//table[@id='sources']/tbody/tr")
        )
        self.assertEqual(row_count, 25, "Should be 25 datasources in the table")
        # go to edit page from datasource list
        self.browser.find_element_by_xpath('//*[@title="edit"]').click()
        btn = self.browser.find_element_by_name("cancel")
        self.assertEqual(
            btn.get_attribute("href"),
            list_url,
            "User should go back to list view when clicking cancel",
        )
        self.browser.find_element_by_name("submit").send_keys("\n")
        self.assertIn(
            "/datasource/",
            self.browser.current_url,
            "User should always return to detail page after submit",
        )
        detail_url = self.live_server_url + f"/datasource/{ds.pk}/"
        self.browser.get(detail_url)
        # go to edit page from datasource detail
        self.browser.find_element_by_xpath('//*[@title="edit"]').click()
        btn = self.browser.find_element_by_name("cancel")
        self.assertEqual(
            btn.get_attribute("href"),
            detail_url,
            "User should go back to detail view when clicking cancel",
        )
        self.browser.find_element_by_name("submit").send_keys("\n")
        self.assertIn(
            "/datasource/",
            self.browser.current_url,
            "User should always return to detail page after submit",
        )

    def test_datagroup(self):
        list_url = self.live_server_url + "/datagroups/"
        self.browser.get(list_url)
        self.browser.find_element_by_xpath('//*[@title="Edit"]').click()
        btn = self.browser.find_element_by_name("cancel")
        self.assertEqual(
            btn.get_attribute("href"),
            list_url,
            "User should go back to list view when clicking cancel",
        )

        dg = DataGroup.objects.first()
        ds_detail_url = f"{self.live_server_url}/datasource/{dg.data_source.pk}/"
        self.browser.get(ds_detail_url)
        self.browser.find_elements_by_xpath('//*[@title="edit"]')[1].send_keys("\n")
        btn = self.browser.find_element_by_name("cancel")
        self.assertEqual(
            btn.get_attribute("href"),
            ds_detail_url,
            "User should go back to detail view when clicking cancel",
        )

        dg_detail_url = f"{self.live_server_url}/datagroup/{dg.pk}/"
        self.browser.get(dg_detail_url)
        self.browser.find_element_by_xpath('//*[@title="Edit"]').send_keys("\n")
        btn = self.browser.find_element_by_name("cancel")
        self.assertEqual(
            btn.get_attribute("href"),
            dg_detail_url,
            "User should go back to detail view when clicking cancel",
        )

        edit_url = f"{self.live_server_url}/datagroup/edit/{dg.pk}/"
        self.browser.get(edit_url)
        self.browser.find_element_by_name("cancel").send_keys("\n")
        self.assertIn(
            "/datagroups/",
            self.browser.current_url,
            "User should always return to detail page after submit",
        )

    @tag("puc")
    def test_product(self):
        doc = self.objects.doc
        doc.file = doc.filename
        doc.save()
        p = self.objects.p
        puc = self.objects.puc
        tag = self.objects.pt
        PUCToTag.objects.create(content_object=puc, tag=tag)
        cm = ProductToPucClassificationMethod.objects.create(
            code="MA", name="Manual", rank=1
        )
        ProductToPUC.objects.create(product=p, puc=puc, classification_method=cm)
        url = self.live_server_url + f"/product/{p.pk}/"
        self.browser.get(url)
        submit = self.browser.find_element_by_id("tag_submit")
        self.assertFalse(submit.is_enabled(), "Button should be disabled")
        tag = self.browser.find_element_by_class_name("taggit-tag")
        tag.click()
        self.assertTrue(submit.is_enabled(), "Button should be enabled")

    def test_field_exclusion(self):
        doc = self.objects.doc
        chem = doc.extractedtext.rawchem.first()
        wait = WebDriverWait(self.browser, 10)

        # The element should not appear on the QA page
        qa_url = self.live_server_url + f"/qa/extractedtext/{doc.pk}/"
        self.browser.get(qa_url)

        wait.until(
            ec.element_to_be_clickable(
                (By.XPATH, f'//*[@id="chemical-update-{chem.pk}"]')
            )
        ).click()

        wait.until(ec.element_to_be_clickable((By.XPATH, "//*[@id='saveChem']")))

        with self.assertRaises(NoSuchElementException):
            self.browser.find_element_by_xpath('//*[@id="id_weight_fraction_type"]')
        with self.assertRaises(NoSuchElementException):
            self.browser.find_element_by_xpath('//*[@id="id_true_cas"]')
        with self.assertRaises(NoSuchElementException):
            self.browser.find_element_by_xpath('//*[@id="id_true_chemname"]')
        with self.assertRaises(NoSuchElementException):
            self.browser.find_element_by_xpath('//*[@id="id_SID"]')
        # make sure the test can pick up one that should be there
        try:
            self.browser.find_element_by_xpath('//*[@id="id_raw_cas"]')
        except NoSuchElementException:
            self.fail("Absence of raw_cas element raised exception")

        # The element should appear when accessed from the datadocument page
        dd_url = self.live_server_url + f"/datadocument/{doc.pk}/"
        self.browser.get(dd_url)

        wait.until(
            ec.element_to_be_clickable(
                (By.XPATH, f'//*[@id="chemical-update-{chem.pk}"]')
            )
        ).click()

        wait.until(ec.element_to_be_clickable((By.XPATH, "//*[@id='saveChem']")))
        try:
            self.browser.find_element_by_xpath('//*[@id="id_weight_fraction_type"]')
        except NoSuchElementException:
            self.fail("Absence of weight_fraction_type element raised exception")

    def test_search_pagination(self):
        self.browser.get(self.live_server_url + "/search/datadocument/?q=d2F0ZXI=")
        wait = WebDriverWait(self.browser, 10)
        links = self.browser.find_elements_by_class_name(f"page-link")
        link = links.pop()
        link.click()
        self.assertIn(
            "&page=", self.browser.current_url, "page parameter should be in URL"
        )
