from asyncio import wait_for

import factory

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait

from dashboard.tests.factories import (
    ExtractedHabitsAndPracticesFactory,
    ExtractedHabitsAndPracticesTagFactory,
    PUCFactory,
)
from dashboard.tests.loader import load_browser


def log_karyn_in(object):
    """
    Log user in for further testing.
    """
    object.browser.get(object.live_server_url + "/login/")
    username_input = object.browser.find_element_by_name("username")
    username_input.send_keys("Karyn")
    password_input = object.browser.find_element_by_name("password")
    password_input.send_keys("specialP@55word")
    object.browser.find_element_by_class_name("btn").click()


class TestHabitsAndPracticesCards(StaticLiveServerTestCase):
    fixtures = ["00_superuser"]

    def setUp(self):
        super().setUpClass()
        self.browser = load_browser()
        log_karyn_in(self)

        self.tags = ExtractedHabitsAndPracticesTagFactory.create_batch(3)
        self.pucs = PUCFactory.create_batch(3, kind="FO")
        self.hnp = ExtractedHabitsAndPracticesFactory.create(
            tags=self.tags, PUCs=self.pucs
        )

    def test_habits_and_practice_cards_populate(self):
        self.browser.get(
            self.live_server_url
            + f"/datadocument/{self.hnp.extracted_text.data_document_id}"
        )
        hnp_card_text = self.browser.find_element_by_id(f"chem-{self.hnp.pk}").text
        self.assertIn(self.hnp.product_surveyed, hnp_card_text)
        self.assertIn(self.hnp.data_type.title, hnp_card_text)
        self.assertIn(self.hnp.notes, hnp_card_text)
        for puc in self.pucs:
            self.assertIn(str(puc), hnp_card_text)
        for tag in self.tags:
            self.assertIn(f"{tag.kind}: {tag.name}", hnp_card_text)

    def test_habits_and_practice_cards_create(self):
        # Set up test data
        hnp_dict = factory.build(dict, FACTORY_CLASS=ExtractedHabitsAndPracticesFactory)
        hnp_dict.get("data_type").save()

        self.browser.get(
            self.live_server_url
            + f"/datadocument/{self.hnp.extracted_text.data_document_id}"
        )
        add_hp_button = self.browser.find_element_by_id(
            "add_chemical"
        ).find_element_by_xpath("button")
        add_hp_button.send_keys("\n")

        # Submit Data to the create form
        create_form = WebDriverWait(self.browser, 10).until(
            expected_conditions.presence_of_element_located((By.ID, "chem-create"))
        )
        create_form.find_element_by_id("id_product_surveyed").send_keys(
            hnp_dict.get("product_surveyed")
        )
        Select(create_form.find_element_by_id("id_data_type")).select_by_visible_text(
            hnp_dict.get("data_type").title
        )
        create_form.find_element_by_id("id_notes").send_keys(hnp_dict.get("notes"))
        create_form.submit()
        self.browser.refresh()

        # Verify data is present on page
        self.assertIn(
            hnp_dict.get("product_surveyed"),
            self.browser.find_element_by_id("cards").text,
        )
        self.assertIn(
            hnp_dict.get("data_type").title,
            self.browser.find_element_by_id("cards").text,
        )
        self.assertIn(
            hnp_dict.get("notes"), self.browser.find_element_by_id("cards").text
        )

    def test_habits_and_practice_cards_edit(self):
        # Set up test data
        hnp_dict = factory.build(dict, FACTORY_CLASS=ExtractedHabitsAndPracticesFactory)
        hnp_dict.get("data_type").save()

        # Open Edit form
        self.browser.get(
            self.live_server_url
            + f"/datadocument/{self.hnp.extracted_text.data_document_id}"
        )
        edit_hp_button = self.browser.find_element_by_id(
            f"chemical-update-{self.hnp.pk}"
        )
        ActionChains(self.browser).move_to_element(edit_hp_button).click().perform()

        # Submit Data to the create form
        edit_form = WebDriverWait(self.browser, 10).until(
            expected_conditions.presence_of_element_located((By.ID, "chem-update"))
        )
        edit_form.find_element_by_id("id_product_surveyed").send_keys(
            hnp_dict.get("product_surveyed")
        )
        Select(edit_form.find_element_by_id("id_data_type")).select_by_visible_text(
            hnp_dict.get("data_type").title
        )
        edit_form.find_element_by_id("id_notes").send_keys(hnp_dict.get("notes"))
        edit_form.submit()
        self.browser.refresh()

        # Verify data is present on page
        self.assertIn(
            hnp_dict.get("product_surveyed"),
            self.browser.find_element_by_id("cards").text,
        )
        self.assertIn(
            hnp_dict.get("data_type").title,
            self.browser.find_element_by_id("cards").text,
        )
        self.assertIn(
            hnp_dict.get("notes"), self.browser.find_element_by_id("cards").text
        )

    def test_habits_and_practice_cards_delete(self):
        self.browser.get(
            self.live_server_url
            + f"/datadocument/{self.hnp.extracted_text.data_document_id}"
        )

        # Assert Card Exists
        self.assertTrue(self.browser.find_elements(By.ID, f"chem-{self.hnp.pk}"))

        delete_hp_button = self.browser.find_element_by_id(
            f"chemical_edit_buttons"
        ).find_element_by_xpath(f"button[@data-target='#chem-delete-{self.hnp.pk}']")
        ActionChains(self.browser).move_to_element(delete_hp_button).click().perform()
        # Confirm Delete
        self.browser.find_element_by_id(f"chemical-modal-save-{self.hnp.pk}").submit()

        # Card No Longer Exists
        self.assertFalse(self.browser.find_elements(By.ID, f"chem-{self.hnp.pk}"))

    def test_habits_and_practice_cards_add_PUC(self):
        # Set up test data
        new_puc = PUCFactory(kind="FO")

        # Open Edit form
        self.browser.get(
            self.live_server_url
            + f"/datadocument/{self.hnp.extracted_text.data_document_id}"
        )
        edit_hp_button = self.browser.find_element_by_id(
            f"chemical-update-{self.hnp.pk}"
        )
        ActionChains(self.browser).move_to_element(edit_hp_button).click().perform()

        # Select and submit the new PUC to the habits and practice
        edit_form = WebDriverWait(self.browser, 10).until(
            expected_conditions.presence_of_element_located((By.ID, "chem-update"))
        )
        edit_form.find_element_by_id("id_PUCs").find_element_by_xpath(
            f"option[@value={new_puc.pk}]"
        ).click()
        edit_form.submit()
        self.browser.refresh()

        # Verify data is present on page
        self.assertIn(
            str(new_puc), self.browser.find_element_by_id(f"chem-{self.hnp.pk}").text
        )

    def test_habits_and_practice_cards_remove_PUC(self):
        # Open Edit form and assert puc present (self.pucs[0] in this case.)
        self.browser.get(
            self.live_server_url
            + f"/datadocument/{self.hnp.extracted_text.data_document_id}"
        )
        self.assertIn(
            str(self.pucs[0]),
            self.browser.find_element_by_id(f"chem-{self.hnp.pk}").text,
        )
        edit_hp_button = self.browser.find_element_by_id(
            f"chemical-update-{self.hnp.pk}"
        )
        ActionChains(self.browser).move_to_element(edit_hp_button).click().perform()

        # Select and submit the new PUC to the habits and practice
        edit_form = WebDriverWait(self.browser, 10).until(
            expected_conditions.presence_of_element_located((By.ID, "chem-update"))
        )
        edit_form.find_element_by_xpath(
            f"//li[@title='{self.pucs[0]}']/span[@role='presentation']"
        ).click()
        edit_form.submit()
        wait_for(self._link_has_gone_stale, 10)

        # Verify data is not present on card
        self.assertNotIn(
            str(self.pucs[0]),
            self.browser.find_element_by_id(f"chem-{self.hnp.pk}").text,
        )

    def _link_has_gone_stale(self):
        """
        This method is a selenium workaround to ensure a page has reloaded.
        It's an automatic part of the form submission action but
        as it can be hard to tell when form processing has finished
        this will instead return true when the page has refreshed itself
        """
        try:
            # poll the link with an arbitrary call
            self.browser.find_elements_by_tag_name("html")
            return False
        except StaleElementReferenceException:
            return True
