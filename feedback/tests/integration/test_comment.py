from django.contrib.auth.models import User
from django.urls import reverse
from selenium.webdriver.common.by import By

from dashboard.tests.loader import load_browser
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec

from feedback.models import Comment
from feedback.tests.factories import CommentFactory
from feedback.tests.utils import log_karyn_in
from feedback.views import CommentCreate


class TestCommentCreation(StaticLiveServerTestCase):
    fixtures = ["00_superuser"]

    def setUp(self):
        self.browser = load_browser()
        # Set the resolution as the navbar is hidden on lower resolutions
        self.browser.set_window_size(1920, 1080)
        self.wait = WebDriverWait(self.browser, 15)

    def tearDown(self):
        self.browser.quit()

    def test_unauthenticated_user_comments(self):
        comment = self._make_comment()
        self.assertIsNone(comment.updated_by)
        self.assertIsNone(comment.created_by)

    def test_authenticated_user_comments(self):
        log_karyn_in(self)
        comment = self._make_comment()
        self.assertEqual(comment.updated_by, User.objects.get(username="karyn"))
        self.assertEqual(comment.created_by, User.objects.get(username="karyn"))

    def _make_comment(self):
        Comment.objects.all().delete()
        comment_dict = CommentFactory.build()
        url = reverse("index")
        self.browser.get(self.live_server_url + url)

        self.browser.find_element_by_xpath("//a[@data-target='#comment-modal']").click()
        self.wait.until(ec.presence_of_element_located((By.ID, "comment-create-form")))
        form = self.browser.find_element_by_id("comment-create-form")

        form.find_element_by_id("id_email").send_keys(comment_dict.email)
        form.find_element_by_id("id_subject").send_keys(comment_dict.subject)
        form.find_element_by_id("id_body").send_keys(comment_dict.body)
        form.find_element_by_xpath("//input[@type='submit']").click()

        self.wait.until(ec.staleness_of(form))
        self.assertIn(
            CommentCreate.SUCCESS_MESSAGE,
            self.browser.find_element_by_xpath("//body").text,
        )

        self.assertEqual(
            Comment.objects.count(), 1, "There should be one newly made comment"
        )
        comment = Comment.objects.first()
        self.assertEqual(comment.email, comment_dict.email)
        self.assertEqual(comment.body, comment_dict.body)
        self.assertEqual(comment.subject, comment_dict.subject)
        self.assertEqual(comment.page_url, url)
        return comment
