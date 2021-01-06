import time

from dashboard.tests.loader import fixtures_standard, load_browser
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from dashboard.models import (
    PUC,
    DSSToxLookup,
    PUCKind,
    DataDocument,
    ExtractedComposition,
)

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec


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
                (By.XPATH, "//*[@id='products_info']"), "Showing 1 to 4 of 4 entries"
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
                "Showing 1 to 1 of 1 entries (filtered from 4 total products)",
            )
        )
        self.assertInHTML(
            "Showing 1 to 1 of 1 entries (filtered from 4 total products)",
            self.browser.find_element_by_xpath("//*[@id='products_info']").text,
        )

        # Data Documents
        wait.until(
            ec.text_to_be_present_in_element(
                (By.XPATH, "//*[@id='documents_info']"), "Showing 1 to 2 of 2 entries"
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
        self.browser.get(
            self.live_server_url + "/chemical/" + chemical.sid + "/puc/" + str(puc.pk)
        )

        # Test the Bubble Plot Legend Zoom occurred
        wait.until(
            ec.visibility_of(self.browser.find_element_by_xpath("//*[@id='card-185']"))
        )
        wait.until(
            ec.text_to_be_present_in_element(
                (By.XPATH, "//*[@id='zoom-to-185']/b"), "hand/body lotion"
            )
        )
        self.assertInHTML(
            "hand/body lotion",
            self.browser.find_element_by_xpath("//*[@id='zoom-to-185']/b").text,
        )
        self.assertFalse(
            self.browser.find_element_by_xpath(
                "//*[@id='card-210']/div/div"
            ).is_displayed()
        )

        # Test that Bubble Plot zoom occurred
        self.assertTrue(
            self.browser.find_element_by_xpath(
                "//*[@id='bubble-label-185']"
            ).is_displayed()
        )
        self.assertFalse(
            self.browser.find_element_by_xpath(
                "//*[@id='bubble-label-210']"
            ).is_displayed()
        )

    def test_only_formulations(self):
        dss = DSSToxLookup.objects.get(sid="DTXSID9022528")
        # add a non-formulation PUC to a product that's related to
        # DTXSID9022528
        dd_id = (
            ExtractedComposition.objects.filter(dsstox=dss).first().extracted_text_id
        )
        dd = DataDocument.objects.get(pk=dd_id)
        p = dd.products.create(title="Test Product")
        p.puc_set.create(
            kind=PUCKind.objects.get(code="OC"), gen_cat="Test Occupational PUC"
        )

        wait = WebDriverWait(self.browser, 10)
        self.browser.get(self.live_server_url + "/chemical/" + dss.sid)
        self.assertNotIn(
            "Test Occupational PUC",
            self.browser.find_element_by_xpath("//*[@id='puc-accordion-FO']").text,
        )

    def test_filter_by_data_group(self):
        """
        All the Products and Documents associated with the Chemical
        should be returned via ajax calls and included in the tables

        For the purpose of this test, the SID coresponds to Ethanol
        """
        chemical = DSSToxLookup.objects.get(sid="DTXSID9020584")
        wait = WebDriverWait(self.browser, 10)
        self.browser.get(self.live_server_url + chemical.get_absolute_url())
        wait.until(
            ec.text_to_be_present_in_element(
                (By.XPATH, "//*[@id='group_type_dropdown']"), "All"
            )
        )
        input_el = self.browser.find_element_by_xpath("//*[@id='group_type_dropdown']")
        input_el.send_keys("Chemical presence list\n")
        wait.until(
            ec.text_to_be_present_in_element(
                (By.XPATH, "//*[@id='group_type_dropdown']"), "Chemical presence list"
            )
        )
        self.assertInHTML(
            "Showing 1 to 3 of 3 entries (filtered from 8 total documents)",
            self.browser.find_element_by_xpath("//*[@id='documents_info']").text,
        )

    def test_filter_by_puc_kind(self):
        """
        All the Products with the Chemical
        should be returned via ajax calls and included in the tables

        For the purpose of this test, the SID coresponds to Water
        """
        chemical = DSSToxLookup.objects.get(sid="DTXSID6026296")
        wait = WebDriverWait(self.browser, 10)
        self.browser.get(self.live_server_url + chemical.get_absolute_url())
        wait.until(
            ec.text_to_be_present_in_element(
                (By.XPATH, "//*[@id='puc_kinds_dropdown']"), "All"
            )
        )
        input_el = self.browser.find_element_by_xpath("//*[@id='puc_kinds_dropdown']")
        input_el.send_keys("Occupation\n")
        wait.until(
            ec.text_to_be_present_in_element(
                (By.XPATH, "//*[@id='puc_kinds_dropdown']"), "Occupation"
            )
        )
        self.assertInHTML(
            "Showing 0 to 0 of 0 entries (filtered from 6 total products)",
            self.browser.find_element_by_xpath("//*[@id='products_info']").text,
        )

    def test_product_table_sort(self):
        chemical = DSSToxLookup.objects.get(sid="DTXSID9022528")
        wait = WebDriverWait(self.browser, 10)
        self.browser.get(self.live_server_url + chemical.get_absolute_url())

        wait.until(
            ec.text_to_be_present_in_element(
                (By.XPATH, "//*[@id='products_info']"), "Showing 1 to 4 of 4 entries"
            )
        )

        product_header = self.browser.find_element_by_xpath(
            "//*[@id='products']/thead/tr/th[1]"
        )
        # table sort by product ascending by default
        first_product = self.browser.find_element_by_xpath(
            "//*[@id='products']/tbody/tr[1]/td[1]"
        )
        self.assertEqual("Lemon Clarifying Shampoo", first_product.text)

        # sort by product descending
        product_header.click()
        time.sleep(1)
        first_product = self.browser.find_element_by_xpath(
            "//*[@id='products']/tbody/tr[1]/td[1]"
        )
        self.assertEqual("Rose Whipped Body Lotion", first_product.text)

        puc_header = self.browser.find_element_by_xpath(
            "//*[@id='products']/thead/tr/th[3]"
        )
        # sort by puc ascending
        puc_header.click()
        time.sleep(1)
        first_puc = self.browser.find_element_by_xpath(
            "//*[@id='products']/tbody/tr[1]/td[3]"
        )

        self.assertEqual("Manufactured formulations", first_puc.text)
        # puc null should be at bottom
        last_puc = self.browser.find_element_by_xpath(
            "//*[@id='products']/tbody/tr[4]/td[3]"
        )
        self.assertEqual("", last_puc.text)

        # sort by puc descending
        puc_header.click()
        time.sleep(1)
        first_puc = self.browser.find_element_by_xpath(
            "//*[@id='products']/tbody/tr[1]/td[3]"
        )
        self.assertEqual(
            "Personal care - hair styling and care - shampoo", first_puc.text
        )

        # puc null should be at bottom
        last_puc = self.browser.find_element_by_xpath(
            "//*[@id='products']/tbody/tr[4]/td[3]"
        )
        self.assertEqual("", last_puc.text)

    def test_filter_by_puc(self):
        """
        All the Products and Documents associated with the Chemical
        should be returned via ajax calls and included in the tables
        """
        chemical = DSSToxLookup.objects.get(sid="DTXSID6026296")
        wait = WebDriverWait(self.browser, 10)
        self.browser.get(self.live_server_url + chemical.get_absolute_url())

        wait.until(
            ec.text_to_be_present_in_element(
                (By.XPATH, "//*[@id='products_info']"), "Showing 1 to 6 of 6 entries"
            )
        )
        # filter by puc
        puc_filter = self.browser.find_element_by_id("filter-137")
        puc_filter.click()
        time.sleep(1)

        self.assertEqual(
            puc_filter.get_attribute("data-original-title"), "Clear filter table by PUC"
        )
        puc_filter_icon = puc_filter.find_element_by_class_name("icon-primary")
        self.assertIsNotNone(puc_filter_icon)

        # Documents table
        self.assertInHTML(
            "Showing 1 to 1 of 1 entries related to PUC Personal care (filtered from 18 total documents)",
            self.browser.find_element_by_xpath("//*[@id='documents_info']").text,
        )
        # Products table
        self.assertInHTML(
            "Showing 1 to 1 of 1 entries related to PUC Personal care (filtered from 6 total products)",
            self.browser.find_element_by_xpath("//*[@id='products_info']").text,
        )

        # Clear filter by puc
        puc_filter.click()
        time.sleep(1)

        self.assertEqual(
            puc_filter.get_attribute("data-original-title"), "Filter table by PUC"
        )
        puc_filter_icon = puc_filter.find_element_by_class_name("icon-secondary")
        self.assertIsNotNone(puc_filter_icon)

        # Documents table
        self.assertInHTML(
            "Showing 1 to 10 of 18 entries",
            self.browser.find_element_by_xpath("//*[@id='documents_info']").text,
        )
        # Products table
        self.assertInHTML(
            "Showing 1 to 6 of 6 entries",
            self.browser.find_element_by_xpath("//*[@id='products_info']").text,
        )

    def test_filter_by_keyword(self):
        """
        All the Products and Documents associated with the Chemical
        should be returned via ajax calls and included in the tables
        """
        chemical = DSSToxLookup.objects.get(sid="DTXSID9020584")
        wait = WebDriverWait(self.browser, 10)
        self.browser.get(self.live_server_url + chemical.get_absolute_url())

        wait.until(
            ec.text_to_be_present_in_element(
                (By.XPATH, "//*[@id='documents_info']"), "Showing 1 to 8 of 8 entries"
            )
        )
        # filter by keyword
        keyword_filter = self.browser.find_element_by_id("keywords-1")
        keyword_filter.click()
        time.sleep(1)

        self.assertEqual(
            keyword_filter.get_attribute("data-original-title"),
            "Clear filter table by Keyword Set",
        )
        keyword_filter_icon = keyword_filter.find_element_by_class_name("icon-primary")
        self.assertIsNotNone(keyword_filter_icon)

        # Documents table
        self.assertInHTML(
            "Showing 1 to 1 of 1 entries related to Keyword { wine, wood, writing } (filtered from 8 total documents)",
            self.browser.find_element_by_xpath("//*[@id='documents_info']").text,
        )

        # Clear filter by keyword
        keyword_filter.click()
        time.sleep(1)

        self.assertEqual(
            keyword_filter.get_attribute("data-original-title"),
            "Filter table by Keyword Set",
        )
        keyword_filter_icon = keyword_filter.find_element_by_class_name(
            "icon-secondary"
        )
        self.assertIsNotNone(keyword_filter_icon)

        # Documents table
        self.assertInHTML(
            "Showing 1 to 8 of 8 entries",
            self.browser.find_element_by_xpath("//*[@id='documents_info']").text,
        )
