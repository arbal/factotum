from django.urls import reverse
from dashboard.tests.factories import (
    FunctionalUseFactory,
    ExtractedCompositionFactory,
    FunctionalUseCategoryFactory,
)
from dashboard.tests.loader import load_browser
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.select import Select
import time


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


class TestFunctionalUseCuration(StaticLiveServerTestCase):
    fixtures = ["00_superuser"]

    def setUp(self):
        self.browser = load_browser()
        self.wait = WebDriverWait(self.browser, 15)

        log_karyn_in(self)

        self.functional_use = FunctionalUseFactory()
        self.functional_use_category = FunctionalUseCategoryFactory()
        self.excomp = ExtractedCompositionFactory.create(
            functional_uses=(self.functional_use,)
        )

    def tearDown(self):
        self.browser.quit()

    def test_functional_use_curation_table_loads(self):
        self.browser.get(self.live_server_url + reverse("functional_use_curation"))

        # Check reported functional use is on the response
        self.wait.until(
            ec.text_to_be_present_in_element(
                (By.ID, "dataGrid"), f"{self.functional_use.report_funcuse}"
            )
        )
        table = self.browser.find_element_by_id("dataGrid")

        # Assert there is a link to the detail curation page.
        self.assertIn(
            reverse(
                "functional_use_curation_chemicals",
                kwargs={"functional_use_pk": self.functional_use.pk},
            ),
            table.get_attribute("innerHTML"),
        )

        # Assert count is correct
        self.assertIn(
            str(self.functional_use.chemicals.count()),
            table.find_element_by_xpath(
                "//div[@col-id='fu_count' and @role='gridcell']"
            ).text,
        )

        # Verify that category cell is editable
        categorycell = table.find_element_by_xpath(
            "//div[@col-id='categorytitle' and @role='gridcell']"
        )
        categorycell.click()

        update_button = self.wait.until(
            ec.element_to_be_clickable((By.XPATH, "//*[@id='applyBtn']"))
        )
        Select(table.find_element_by_id("category_id")).select_by_visible_text(
            self.functional_use_category.title
        )
        update_button.click()
        time.sleep(1)

        self.functional_use.refresh_from_db()
        self.assertTrue(self.functional_use.category == self.functional_use_category)
        self.assertIn(self.functional_use_category.title, categorycell.text)

    def test_functional_use_curation_chemicals_table_loads(self):
        uncurated_excomp = ExtractedCompositionFactory.create(
            functional_uses=(self.functional_use,), is_curated=False
        )
        # Unnamed Chemical
        ExtractedCompositionFactory.create(
            functional_uses=(self.functional_use,), is_curated=False, raw_chem_name=""
        )

        self.browser.get(
            self.live_server_url
            + reverse(
                "functional_use_curation_chemicals",
                kwargs={"functional_use_pk": self.functional_use.pk},
            )
        )

        # Check reported functional use is on the response
        self.wait.until(
            ec.text_to_be_present_in_element(
                (By.ID, "table"), f"{self.excomp.dsstox.true_chemname}"
            )
        )

        table = self.browser.find_element_by_id("table")
        self.assertIn(uncurated_excomp.raw_chem_name, table.text)
        self.assertIn("Unnamed Chemical", table.text)
        # Assert there is a link to the data document page.
        self.assertIn(
            reverse("data_document", kwargs={"pk": self.excomp.extracted_text.pk}),
            table.get_attribute("innerHTML"),
        )

    def test_functional_use_cleanup(self):
        self.browser.get(self.live_server_url + reverse("functional_use_curation"))

        # Check reported functional use is on the response
        self.wait.until(
            ec.text_to_be_present_in_element(
                (By.ID, "dataGrid"), f"{self.functional_use.report_funcuse}"
            )
        )

        # delete chemical
        self.excomp.delete()

        # invoke cleanup button
        remove_button = self.browser.find_element_by_id("delete-fu-btn")
        remove_button.click()
        self.wait.until(ec.element_to_be_clickable((By.ID, "remove-fu-confirm-btn")))
        self.browser.find_element_by_id("remove-fu-confirm-btn").click()
        self.wait.until(
            ec.text_to_be_present_in_element(
                (By.CLASS_NAME, "alert-success"),
                "1 reported functional use(s) successfully removed",
            )
        )
        self.assertIn(
            "No Rows To Show",
            self.browser.find_element_by_id("dataGrid").get_attribute("innerHTML"),
        )
