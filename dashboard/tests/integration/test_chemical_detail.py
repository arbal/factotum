from dashboard.tests.loader import fixtures_standard, load_browser
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from dashboard.models import PUC, DSSToxLookup, Product, DataDocument

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


class TestChemicalDetail(StaticLiveServerTestCase):
    fixtures = fixtures_standard

    def setUp(self):
        self.browser = load_browser()
        log_karyn_in(self)

    def tearDown(self):
        self.browser.quit()

    def test_chemical_detail_datatables(self):
        """
        All the Products and Documents associated with the Chemical
        should be returned via ajax calls and included in the tables
        """
        chemical = DSSToxLookup.objects.get(sid="DTXSID9022528")
        puc = PUC.objects.get(pk=185)
        wait = WebDriverWait(self.browser, 10)
        self.browser.get(self.live_server_url + chemical.get_absolute_url())

        wait.until(
            ec.text_to_be_present_in_element(
                (By.XPATH, "//*[@id='products_info']"),
                "Showing 1 to 4 of 4 entries",
            )
        )
        self.assertInHTML(
            "Showing 1 to 4 of 4 entries",
            self.browser.find_element_by_xpath("//*[@id='products_info']").text,
        )

        input_el = self.browser.find_element_by_xpath(
            '//*[@id="products_filter"]/descendant::input[1]'
        )
        input_el.send_keys("Lemon\n")
        wait.until(
            ec.text_to_be_present_in_element(
                (By.XPATH, "//*[@id='products_info']"),
                "Showing 1 to 1 of 1 entries (filtered from 4 total entries)",
            )
        )
        self.assertInHTML(
            "Showing 1 to 1 of 1 entries (filtered from 4 total entries)",
            self.browser.find_element_by_xpath("//*[@id='products_info']").text,
        )

        # Data Documents
        wait.until(
            ec.text_to_be_present_in_element(
                (By.XPATH, "//*[@id='documents_info']"),
                "Showing 1 to 2 of 2 entries",
            )
        )
        self.assertInHTML(
            "Showing 1 to 2 of 2 entries",
            self.browser.find_element_by_xpath("//*[@id='documents_info']").text,
        )

    def test_chemical_detail_with_puc(self):
        chemical = DSSToxLookup.objects.get(sid="DTXSID9022528")
        puc = PUC.objects.get(pk=185)
        wait = WebDriverWait(self.browser, 10)
        self.browser.get(self.live_server_url + "/chemical/" + chemical.sid + "/puc/" + str(puc.pk))

        # Test the Bubble Plot Legend Zoom occurred
        wait.until(
            ec.visibility_of(self.browser.find_element_by_xpath("//*[@id='card-185']"))
        )
        self.assertInHTML(
            "hand/body lotion",
            self.browser.find_element_by_xpath("//*[@id='card-185']/div/div/b").text,
        )
        self.assertFalse(self.browser.find_element_by_xpath("//*[@id='card-210']/div/div").is_displayed())

        # Test that Bubble Plot zoom occurred
        self.assertTrue(self.browser.find_element_by_xpath("//*[@id='bubble-label-185']").is_displayed())
        self.assertFalse(self.browser.find_element_by_xpath("//*[@id='bubble-label-210']").is_displayed())

