from django.contrib.staticfiles.testing import StaticLiveServerTestCase

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
    body = object.browser.find_element_by_tag_name("body")
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
