from selenium.webdriver import ActionChains
from django.test import tag
from dashboard.tests.loader import fixtures_standard, load_browser
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from dashboard.models import PUC

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.common.exceptions import NoSuchElementException


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


@tag("puc")
class TestPUCProductAndDocumentTables(StaticLiveServerTestCase):
    fixtures = fixtures_standard

    def setUp(self):
        self.browser = load_browser()
        log_karyn_in(self)

    def tearDown(self):
        self.browser.quit()

    def test_puc_product_datatable(self):
        """
        All the Products, Chemicals, and Documents associated with the PUC 
        should be returned via ajax calls and included in the tables
        """
        puc = PUC.objects.get(pk=185)
        wait = WebDriverWait(self.browser, 10)
        self.browser.get(self.live_server_url + puc.get_absolute_url())

        # Products
        input_el = self.browser.find_element_by_xpath(
            '//*[@id="products_filter"]/descendant::input[1]'
        )
        input_el.send_keys("Calgon\n")
        wait.until(
            ec.text_to_be_present_in_element(
                (By.XPATH, "//*[@id='products_info']"),
                "Showing 1 to 1 of 1 entries (filtered from 3 total entries)",
            )
        )
        self.assertInHTML(
            "Showing 1 to 1 of 1 entries (filtered from 3 total entries)",
            self.browser.find_element_by_xpath("//*[@id='products_info']").text,
        )

        # Data Documents
        doc_btn = self.browser.find_element_by_id("document-tab-header")
        doc_btn.click()
        wait.until(
            ec.text_to_be_present_in_element(
                (By.XPATH, "//*[@id='documents']/tbody/tr[1]/td[1]/a"),
                "body butter (PLP) Recertification",
            )
        )

        # Chemicals
        chem_btn = self.browser.find_element_by_id("chemical-tab-header")
        chem_btn.click()
        wait.until(
            ec.text_to_be_present_in_element(
                (By.XPATH, "//*[@id='chemicals']/tbody/tr/td[1]/a"), "DTXSID9022528"
            )
        )
        self.assertInHTML(
            "Download All Chemicals Associated with PUC",
            self.browser.find_element_by_xpath(
                "//button[contains(@class, 'btn-dl-chemical')]"
            ).text,
        )

    def test_additional_statistics_links_open_appropriate_table(self):
        puc = PUC.objects.get(pk=185)
        wait = WebDriverWait(self.browser, 10)
        actions = ActionChains(self.browser)

        self.browser.get(self.live_server_url + puc.get_absolute_url())

        # Data Documents
        doc_btn = self.browser.find_element_by_xpath(
            "//div[@id='puc_stats']//a[@onclick=\"activateTable('#document-tab-header')\"]"
        )
        actions.move_to_element(doc_btn).click().perform()
        wait.until(
            ec.text_to_be_present_in_element(
                (By.XPATH, "//*[@id='documents']/tbody/tr[1]/td[1]/a"),
                "body butter (PLP) Recertification",
            )
        )

        # Chemicals
        chem_btn = self.browser.find_element_by_xpath(
            "//div[@id='puc_stats']//a[@onclick=\"activateTable('#chemical-tab-header')\"]"
        )
        actions.move_to_element(chem_btn).click().perform()
        wait.until(
            ec.text_to_be_present_in_element(
                (By.XPATH, "//*[@id='chemicals']/tbody/tr/td[1]/a"), "DTXSID9022528"
            )
        )

        # Products
        prod_btn = self.browser.find_element_by_xpath(
            "//div[@id='puc_stats']//a[@onclick=\"activateTable('#product-tab-header')\"]"
        )
        actions.move_to_element(prod_btn).click().perform()
        wait.until(
            ec.text_to_be_present_in_element(
                (By.XPATH, "//*[@id='products']/tbody/tr[3]/td[1]/a"),
                "Rose Whipped Body Lotion",
            )
        )
