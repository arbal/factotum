from django.urls import reverse
from django.test import tag
from dashboard.tests.factories import ProductFactory, PUCFactory, ProductToPUCFactory
from dashboard.tests.loader import load_browser
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from dashboard.models import ProductToPucClassificationMethod, ProductToPUC

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


@tag("puc")
class TestBulkRemoveProductPUCTable(StaticLiveServerTestCase):
    fixtures = ["00_superuser"]

    def setUp(self):
        self.browser = load_browser()
        self.wait = WebDriverWait(self.browser, 15)

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

        # Verify the td data
        # xpath uses 1-based indexing.
        self.assertEqual(
            self.browser.find_element_by_xpath("//td[2]").text, self.product.title
        )
        self.assertEqual(
            self.browser.find_element_by_xpath("//td[3]").text,
            self.product.manufacturer,
        )
        self.assertEqual(
            self.browser.find_element_by_xpath("//td[4]").text, self.product.brand_name
        )
        self.assertEqual(
            self.browser.find_element_by_xpath("//td[5]").text,
            self.high_classification.name,
        )

    def test_puc_product_datatable_deletes(self):
        """Loads the table then associates a new tag.
        """
        pk = self.p2p.pk

        self.browser.get(self.live_server_url + reverse("bulk_remove_product_puc"))

        # UberPUC filtering should only show one entry on secondary puc
        self._select_puc(self.secondary_puc.prod_type, self.secondary_puc)
        self.wait.until(
            ec.text_to_be_present_in_element(
                (By.ID, "products_info"), "Showing 1 to 1 of 1 entries"
            )
        )

        # Load the data for the puc
        self._select_puc(self.puc.prod_type)
        self.wait.until(
            ec.text_to_be_present_in_element(
                (By.ID, "products_info"), "Showing 1 to 1 of 1 entries"
            )
        )

        # Select first (only) row the submit the form.
        form = self.browser.find_element_by_id(
            "remove-p2p-form"
        )  # This is just used to determine when refresh is done
        self.browser.find_element_by_xpath(
            "//table[@id='products']/tbody/tr[1]/td[1]"
        ).click()
        self.browser.find_element_by_xpath("//button[@type='submit']").click()
        # Accept confirmation
        alert = self.wait.until(ec.alert_is_present())
        alert.accept()
        self.wait.until(ec.staleness_of(form))

        # Verify P2P connection was deleted
        self.assertFalse(ProductToPUC.objects.filter(pk=pk).exists())
        self._select_puc(self.puc.prod_type)
        self.wait.until(
            ec.text_to_be_present_in_element(
                (By.ID, "products_info"), "Showing 0 to 0 of 0 entries"
            )
        )

        # Verify The new uberpuc shows up on the secondary PUC
        self._select_puc(self.secondary_puc.prod_type, self.secondary_puc)
        self.wait.until(
            ec.text_to_be_present_in_element(
                (By.ID, "products_info"), "Showing 1 to 2 of 2 entries"
            )
        )

    def test_dismiss_confirmation_dismiss(self):
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

        # Select first (only) row the submit the form.
        self.browser.find_element_by_xpath(
            "//table[@id='products']/tbody/tr[1]/td[1]"
        ).click()
        self.browser.find_element_by_xpath("//button[@type='submit']").click()
        # Dismiss confirmation
        alert = self.wait.until(ec.alert_is_present())
        alert.dismiss()

        self.assertTrue(ProductToPUC.objects.filter(pk=self.p2p.pk).exists())

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

        # Verify the td data
        # xpath uses 1-based indexing.
        self.assertEqual(
            self.browser.find_element_by_xpath("//td[2]").text, self.product.title
        )
        self.assertEqual(
            self.browser.find_element_by_xpath("//td[3]").text,
            self.product.manufacturer,
        )
        self.assertEqual(
            self.browser.find_element_by_xpath("//td[4]").text, self.product.brand_name
        )
        self.assertEqual(
            self.browser.find_element_by_xpath("//td[5]").text,
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
        self.p2p = ProductToPUCFactory(
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
        self.non_meta_p2p = ProductToPUCFactory(
            product=self.product,
            puc=self.secondary_puc,
            classification_method=low_classification,
        )

    def _select_puc(self, searchterm, puc=None):
        # PUC to compare against
        if puc is None:
            puc = self.puc

        self.browser.find_element_by_class_name("select2-selection__arrow").click()
        select2search = self.browser.find_element_by_class_name("select2-search__field")
        select2search.send_keys(searchterm)
        self.wait.until(
            ec.text_to_be_present_in_element(
                (By.XPATH, "//*[@class='select2-results']"), puc.prod_type
            )
        )
        select2search.send_keys("\n")
