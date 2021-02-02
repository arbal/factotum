import factory
import time

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
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
        self.wait = WebDriverWait(self.browser, 10)
        log_karyn_in(self)

        self.tags = ExtractedHabitsAndPracticesTagFactory.create_batch(3)
        self.pucs = PUCFactory.create_batch(3)
        self.hnp = ExtractedHabitsAndPracticesFactory.create(
            tags=self.tags, PUCs=self.pucs
        )

    def tearDown(self):
        self.browser.quit()

    def test_habits_and_practice_cards_populate(self):
        self.browser.get(
            self.live_server_url
            + f"/datadocument/{self.hnp.extracted_text.data_document_id}"
        )
        hnp_card_text = self.wait.until(
            expected_conditions.presence_of_element_located(
                (By.ID, f"chem-{self.hnp.pk}")
            )
        ).text
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
        add_hp_button = self.wait.until(
            expected_conditions.presence_of_element_located((By.ID, "add_chemical"))
        ).find_element_by_xpath("button")
        add_hp_button.send_keys("\n")

        # Submit Data to the create form
        create_form = self.wait.until(
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
        time.sleep(1)
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
        edit_hp_button = self.wait.until(
            expected_conditions.presence_of_element_located(
                (By.ID, f"chemical-update-{self.hnp.pk}")
            )
        )
        ActionChains(self.browser).move_to_element(edit_hp_button).click().perform()

        # Submit Data to the create form
        edit_form = self.wait.until(
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
        time.sleep(1)
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

        # Verify card exists
        self.wait.until(
            expected_conditions.presence_of_element_located(
                (By.ID, f"chem-{self.hnp.pk}")
            )
        )

        delete_hp_button = self.browser.find_element_by_id(
            f"chem-{{ self.hnp.pk }}-buttons"
        ).find_element_by_xpath(f"button[@data-target='#chem-delete-{self.hnp.pk}']")
        ActionChains(self.browser).move_to_element(delete_hp_button).click().perform()
        # Confirm Delete
        self.browser.find_element_by_id(f"chemical-modal-save-{self.hnp.pk}").submit()

        # Card No Longer Exists
        self.assertFalse(self.browser.find_elements(By.ID, f"chem-{self.hnp.pk}"))

    def test_habits_and_practice_cards_add_PUC(self):
        # Set up test data
        new_puc = PUCFactory()

        # Open Edit form
        self.browser.get(
            self.live_server_url
            + f"/datadocument/{self.hnp.extracted_text.data_document_id}"
        )
        edit_hp_button = self.wait.until(
            expected_conditions.presence_of_element_located(
                (By.ID, f"chemical-update-{self.hnp.pk}")
            )
        )
        ActionChains(self.browser).move_to_element(edit_hp_button).click().perform()

        # Select and submit the new PUC to the habits and practice
        edit_form = self.wait.until(
            expected_conditions.presence_of_element_located((By.ID, "chem-update"))
        )
        edit_form.find_element_by_id("id_PUCs").find_element_by_xpath(
            f"option[@value={new_puc.pk}]"
        ).click()
        edit_form.submit()
        self.browser.refresh()
        time.sleep(1)
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
            self.wait.until(
                expected_conditions.presence_of_element_located(
                    (By.ID, f"chem-{self.hnp.pk}")
                )
            ).text,
        )
        edit_hp_button = self.browser.find_element_by_id(
            f"chemical-update-{self.hnp.pk}"
        )
        ActionChains(self.browser).move_to_element(edit_hp_button).click().perform()

        # Select and submit the new PUC to the habits and practice
        edit_form = self.wait.until(
            expected_conditions.presence_of_element_located((By.ID, "chem-update"))
        )

        # There should be a front end way of removing an element from select2 autocomplete forms.
        #  However it's not working.  Nuking the entire selection with JS instead.
        # edit_form.find_element_by_xpath(
        #     f"//li[@title='{self.pucs[0]}']/span[@role='presentation']"
        # ).click()
        self.browser.execute_script("$('#id_PUCs').val(null).trigger('change');")
        stale_element = self.browser.find_elements_by_tag_name("html")[0]
        edit_form.submit()

        WebDriverWait(self.browser, 60).until(
            expected_conditions.staleness_of(stale_element)
        )
        time.sleep(1)
        # Verify data is not present on card
        self.assertNotIn(
            str(self.pucs[0]),
            self.browser.find_element_by_id(f"chem-{self.hnp.pk}").text,
        )

    def test_habits_and_practice_cards_add_tag(self):
        # Set up test data
        new_tag = ExtractedHabitsAndPracticesTagFactory()

        # Open Edit form
        self.browser.get(
            self.live_server_url
            + f"/datadocument/{self.hnp.extracted_text.data_document_id}"
        )
        chem_card = self.wait.until(
            expected_conditions.presence_of_element_located(
                (By.ID, f"chem-click-{self.hnp.pk}")
            )
        )

        # Select and submit the new PUC to the habits and practice
        ActionChains(self.browser).move_to_element(chem_card).click().perform()

        self.browser.implicitly_wait(10)

        # Verify the card was selected
        self.assertEqual(
            str(self.hnp.pk),
            Select(self.browser.find_element_by_id("id_chems")).options[0].value,
        )
        tagform = self.browser.find_element_by_xpath(
            "//form[contains(@action,'/save_tags/"
            f"{self.hnp.extracted_text.data_document_id}/')]"
        )
        dal_textbox = tagform.find_element_by_xpath("*//span[@role='combobox']")
        dal_textbox.send_keys(new_tag.name)
        # Wait for autocomplete to return
        WebDriverWait(self.browser, 20).until(
            expected_conditions.text_to_be_present_in_element(
                (By.ID, "select2-id_tags-results"), new_tag.name
            )
        )
        dal_textbox.send_keys("\n")
        stale_element = self.browser.find_elements_by_tag_name("html")[0]
        tagform.submit()
        WebDriverWait(self.browser, 60).until(
            expected_conditions.staleness_of(stale_element)
        )

        # Verify data is present on page
        self.assertIn(
            f"{new_tag.kind.name}: {new_tag.name}",
            self.browser.find_element_by_id(f"chem-{self.hnp.pk}").text,
        )

    def test_habits_and_practice_cards_remove_tag(self):
        # Open Edit form and assert tag present (self.tags[0] in this case.)
        self.browser.get(
            self.live_server_url
            + f"/datadocument/{self.hnp.extracted_text.data_document_id}"
        )
        card = self.wait.until(
            expected_conditions.presence_of_element_located(
                (By.ID, f"chem-{self.hnp.pk}")
            )
        )
        self.assertIn(f"{self.tags[0].kind.name}: {self.tags[0].name}", card.text)

        # Delete
        tag_delete_button = self.browser.find_element_by_xpath(
            f"//button[@data-target='#tag-delete-{self.hnp.pk}-{self.tags[0].pk}']"
        )
        ActionChains(self.browser).move_to_element(tag_delete_button).click().perform()

        # Confirm (submit to avoid modal animation)
        self.browser.find_element_by_id(f"hp-modal-save-{self.hnp.pk}").submit()

        # Wait for refresh
        stale_element = self.browser.find_elements_by_tag_name("html")[0]
        self.browser.refresh()
        WebDriverWait(self.browser, 60).until(
            expected_conditions.staleness_of(stale_element)
        )

        card = self.wait.until(
            expected_conditions.presence_of_element_located(
                (By.ID, f"chem-{self.hnp.pk}")
            )
        )
        # Verify data is not present on card
        self.assertNotIn(f"{self.tags[0].kind.name}: {self.tags[0].name}", card.text)
