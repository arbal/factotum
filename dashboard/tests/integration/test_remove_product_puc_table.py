from django.urls import reverse

from dashboard.tests.factories import ProductFactory, PUCFactory, ProductToPUCFactory
from dashboard.tests.loader import load_browser
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from dashboard.models import ProductToPucClassificationMethod

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


class TestBulkRemoveProductPUCTable(StaticLiveServerTestCase):
    fixtures = ["00_superuser"]

    def setUp(self):
        self.browser = load_browser()
        self.wait = WebDriverWait(self.browser, 10)

        log_karyn_in(self)

        self._build_data()

    def tearDown(self):
        self.browser.quit()

    def test_puc_product_datatable_loads(self):
        """Loads the table then associates a new tag.
        """
        self.browser.get(self.live_server_url + reverse("bulk_remove_product_puc"))

        # Load the data for the puc
        self._select_puc(self.puc.prod_type)
        self.wait.until(
            ec.text_to_be_present_in_element(
                (By.ID, "products_info"), "Showing 1 to 1 of 1 entries"
            )
        )

        # Verify the 2nd td is the product title, the 3rd td is the classification method name
        # xpath uses 1-based indexing.
        self.assertEqual(
            self.browser.find_element_by_xpath("//td[2]").text, self.product.title
        )
        self.assertEqual(
            self.browser.find_element_by_xpath("//td[3]").text,
            self.high_classification.name,
        )

    def test_puc_product_datatable_searches(self):
        # make a new product to be filtered by search but not by puc.
        ProductToPUCFactory(
            product=ProductFactory(),
            puc=self.puc,
            classification_method=self.high_classification,
        )

        self.browser.get(self.live_server_url + reverse("bulk_remove_product_puc"))

        # Load the data for the puc
        self._select_puc(self.puc.prod_type)
        # Verify both rows have loaded.
        self.wait.until(
            ec.text_to_be_present_in_element(
                (By.ID, "products_info"), "Showing 1 to 2 of 2 entries"
            )
        )

        self.browser.find_element_by_xpath(
            "//div[@id='products_filter']//input"
        ).send_keys(self.product.title)

        # Load the newly search filtered data
        self._select_puc(self.puc.prod_type)
        self.wait.until(
            ec.text_to_be_present_in_element(
                (By.ID, "products_info"), "Showing 1 to 1 of 1 entries"
            )
        )

        # Verify the 2nd td is the product title, the 3rd td is the classification method name
        # xpath uses 1-based indexing.
        self.assertEqual(
            self.browser.find_element_by_xpath("//td[2]").text, self.product.title
        )
        self.assertEqual(
            self.browser.find_element_by_xpath("//td[3]").text,
            self.high_classification.name,
        )

    def test_puc_product_datatable_classification_method_filter(self):
        self.browser.get(self.live_server_url + reverse("bulk_remove_product_puc"))

        classification_methods = self.browser.find_elements_by_xpath(
            "//div[@id='classification-methods']//input"
        )
        # Verify all classification methods have loaded.
        self.assertEqual(
            len(classification_methods),
            ProductToPucClassificationMethod.objects.count(),
        )

        # Load the data for the puc
        self._select_puc(self.puc.prod_type)
        self.wait.until(
            ec.text_to_be_present_in_element(
                (By.ID, "products_info"), "Showing 1 to 1 of 1 entries"
            )
        )

        # find the manual filter input and click it.
        next(
            cm_filter
            for cm_filter in classification_methods
            if cm_filter.get_attribute("value") == self.high_classification.code
        ).click()

        self.wait.until(
            ec.text_to_be_present_in_element(
                (By.ID, "products_info"), "Showing 0 to 0 of 0 entries"
            )
        )

    def _build_data(self):
        # Add Classification types
        self.high_classification = ProductToPucClassificationMethod(
            code="MA", name="Manual", rank=1
        )
        low_classification = ProductToPucClassificationMethod(
            code="AU", name="Automatic", rank=5
        )
        self.high_classification.save()
        low_classification.save()

        # Make some pucs.
        #   - puc will be the uberpuc for testing
        #   - secondary_puc will be used to demonstrate this filters non-uber products
        self.puc = PUCFactory()
        self.secondary_puc = PUCFactory()

        # Make some products.
        #   - product will be linked to this puc via uberpuc
        #   - filtered_product will be linked to this puc but linked to the secondary puc by uberpuc
        self.product = ProductFactory()
        self.filtered_product = ProductFactory()

        # Connect products to pucs
        # Uber pucs
        ProductToPUCFactory(
            product=self.product,
            puc=self.puc,
            classification_method=self.high_classification,
        )
        ProductToPUCFactory(
            product=self.filtered_product,
            puc=self.secondary_puc,
            classification_method=self.high_classification,
        )

        # Non-uber puc
        ProductToPUCFactory(
            product=self.filtered_product,
            puc=self.secondary_puc,
            classification_method=low_classification,
        )

    def _select_puc(self, searchterm):
        self.browser.find_element_by_class_name("select2-selection__arrow").click()
        select2search = self.browser.find_element_by_class_name("select2-search__field")
        select2search.send_keys(searchterm)
        self.wait.until(
            ec.text_to_be_present_in_element(
                (By.XPATH, "//*[@class='select2-results']"), self.puc.prod_type
            )
        )
        select2search.send_keys("\n")
