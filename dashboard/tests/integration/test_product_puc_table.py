from django.urls import reverse
from selenium.webdriver.support.select import Select
from django.test import tag

from dashboard.tests.factories import ProductFactory, PUCFactory, ProductToPUCFactory
from dashboard.tests.loader import load_browser
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from dashboard.models import ProductToPucClassificationMethod, PUCTag, PUCToTag

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
class TestBulkProductPUCTable(StaticLiveServerTestCase):
    fixtures = ["00_superuser"]

    def setUp(self):
        self.browser = load_browser()
        self.wait = WebDriverWait(self.browser, 10)

        log_karyn_in(self)

        self._build_data()

    def tearDown(self):
        self.browser.quit()

    def test_puc_product_datatable(self):
        """Loads the table then associates a new tag.
        """
        assert self.product.tags.count() == 0

        self.browser.get(self.live_server_url + reverse("bulk_product_tag"))

        # Load the data for the puc
        self._select_puc(self.puc.prod_type)
        self.wait.until(
            ec.text_to_be_present_in_element(
                (By.ID, "products_info"), "Showing 1 to 1 of 1 entries"
            )
        )
        # Select a tag
        Select(self.browser.find_element_by_id("id_tag")).select_by_value(
            f"{self.tag.pk}"
        )
        # Select the only row
        self.browser.find_element_by_xpath("//table[@id='products']//th").click()
        # Save
        self.browser.find_element_by_id("btn-assign-puc").click()
        # Verify
        self.wait.until(
            ec.text_to_be_present_in_element(
                (By.CSS_SELECTOR, "body"),
                f'The "{self.tag.name}" Attribute was assigned to 1 Product(s).',
            )
        )

        assert self.product.tags.count() == 1
        assert self.product.tags.first() == self.tag

    def _build_data(self):
        # Add Classification types
        high_classification = ProductToPucClassificationMethod(
            code="MA", name="Manual", rank=1
        )
        low_classification = ProductToPucClassificationMethod(
            code="AU", name="Automatic", rank=5
        )
        high_classification.save()
        low_classification.save()

        # Make some pucs.
        #   - puc will be the uberpuc for testing
        #   - secondary_puc will be used to demonstrate this filters non-uber products
        self.puc = PUCFactory()
        self.secondary_puc = PUCFactory()
        # Add a tag to the main puc
        self.tag = PUCTag.objects.create(name="tag", slug="tag")
        PUCToTag.objects.create(content_object=self.puc, tag=self.tag, assumed=False)

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
            classification_method=high_classification,
        )
        ProductToPUCFactory(
            product=self.filtered_product,
            puc=self.secondary_puc,
            classification_method=high_classification,
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
