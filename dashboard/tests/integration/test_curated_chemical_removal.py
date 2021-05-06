from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait

from dashboard.tests.loader import fixtures_standard, load_browser
from django.contrib.staticfiles.testing import StaticLiveServerTestCase


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


class TestCuratedChemicalRemoval(StaticLiveServerTestCase):
    fixtures = fixtures_standard

    def setUp(self):
        self.browser = load_browser()
        log_karyn_in(self)

    def tearDown(self):
        self.browser.quit()

    def test_index_page_table(self):
        index_url = self.live_server_url + "/curated_chemical_removal/"
        self.browser.get(index_url)

        self.wait = WebDriverWait(self.browser, 10)
        search_form = self.wait.until(
            expected_conditions.presence_of_element_located((By.ID, "search_chem_form"))
        )
        with self.assertRaises(NoSuchElementException):
            self.browser.find_element_by_id("curated_chemicals_info")

        # search chlorine
        search_form.find_element_by_id("search_chem_text").send_keys("chlorine\n")
        self.wait.until(
            expected_conditions.text_to_be_present_in_element(
                (By.ID, "curated_chemicals_info"), "Showing 1 to 1 of 1 entries"
            )
        )
        sid_cell = self.browser.find_element_by_xpath(
            '//*[@id="curated_chemicals"]/tbody/tr[1]/td[1]'
        )
        raw_name_cell = self.browser.find_element_by_xpath(
            '//*[@id="curated_chemicals"]/tbody/tr[1]/td[2]'
        )
        raw_cas_cell = self.browser.find_element_by_xpath(
            '//*[@id="curated_chemicals"]/tbody/tr[1]/td[3]'
        )
        curated_name_cell = self.browser.find_element_by_xpath(
            '//*[@id="curated_chemicals"]/tbody/tr[1]/td[4]'
        )
        curated_cas_cell = self.browser.find_element_by_xpath(
            '//*[@id="curated_chemicals"]/tbody/tr[1]/td[5]'
        )
        count_cell = self.browser.find_element_by_xpath(
            '//*[@id="curated_chemicals"]/tbody/tr[1]/td[6]'
        )
        self.assertIn("DTXSID1020273", sid_cell.text)
        self.assertIn("Chlorine", raw_name_cell.text)
        self.assertIn("7782-50-5", raw_cas_cell.text)
        self.assertIn("chlorine", curated_name_cell.text)
        self.assertIn("7782-50-5", curated_cas_cell.text)
        self.assertEqual("3", count_cell.text)