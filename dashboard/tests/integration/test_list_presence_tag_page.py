from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait

from dashboard.models import DataDocument
from dashboard.tests.factories import (
    ExtractedListPresenceFactory,
    ExtractedListPresenceTagFactory,
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


class TestListPresenceTag(StaticLiveServerTestCase):
    fixtures = ["00_superuser"]

    def setUp(self):
        super().setUpClass()
        self.browser = load_browser()
        log_karyn_in(self)

        self.main_tag = ExtractedListPresenceTagFactory()
        self.additional_tag = ExtractedListPresenceTagFactory()
        # Make 2 extracted list presences with different
        # one with tags [tags[0]] and one with tags [tags[0],tags[1]]
        ExtractedListPresenceFactory(tags=[self.main_tag])
        ExtractedListPresenceFactory(tags=[self.main_tag, self.additional_tag])

    def test_list_presence_tag_page(self):
        self.browser.get(
            self.live_server_url + f"/list_presence_tag/{self.main_tag.pk}"
        )

        # Verify core data is present
        self.assertIn(
            self.main_tag.name.capitalize(),
            self.browser.find_element_by_css_selector("body").text,
        )
        self.assertIn(
            self.main_tag.kind.name.capitalize(),
            self.browser.find_element_by_css_selector("body").text,
        )
        self.assertIn(
            self.main_tag.definition,
            self.browser.find_element_by_css_selector("body").text,
        )

        wait = WebDriverWait(self.browser, 10)

        tagset_count = len(self.main_tag.get_tagsets())
        tagset_string = f"Showing 1 to {tagset_count} of {tagset_count} entries"
        wait.until(
            expected_conditions.text_to_be_present_in_element(
                (By.ID, "tagset_table_info"), tagset_string
            )
        )

        self.browser.find_element_by_id("document-tab").click()

        document_count = DataDocument.objects.count()
        document_string = f"Showing 1 to {document_count} of {document_count} entries"
        wait.until(
            expected_conditions.text_to_be_present_in_element(
                (By.ID, "document_table_info"), document_string
            )
        )
