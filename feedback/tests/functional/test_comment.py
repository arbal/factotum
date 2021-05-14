from django.shortcuts import render
from django.test import TestCase, RequestFactory
from django.urls import reverse
from lxml import html

from feedback.views import CommentCreate as CommentView
from feedback.forms import CommentForm


class TestComment(TestCase):
    create_path_name = "feedback:comment_create"

    # Test that GET requests to feedback:comment return a page built using core and feedback templates.
    def test_get_create_view(self):
        response = self.client.get(reverse(self.create_path_name))

        self.assertEqual(200, response.status_code)
        self.assertEqual(
            CommentView.as_view().__name__, response.resolver_match.func.__name__
        )

        self.assertTemplateUsed(response, template_name="core/bs4_form.html")
        self.assertTemplateUsed(
            response, template_name="feedback/comment_create_modal.html"
        )

    # Test that valid POST data returns a "200 - OK" status code
    def test_post_valid_data_create_comment(self):
        response = self.client.post(
            reverse(self.create_path_name),
            {
                "email": "test@epa.gov",
                "body": "Valid body",
                "subject": "Valid subject",
                "path_url": "/",
            },
        )

        self.assertEquals(response.status_code, 200)

    # Test that invalid POST data returns a "400 - Bad Request" status code
    # and that error messages are returned.
    def test_post_invalid_data_create_comment(self):
        blank_response = self.client.post(reverse(self.create_path_name), {})
        invalid_email_response = self.client.post(
            reverse(self.create_path_name), {"email": "test@email.com"}
        )

        self.assertEqual(400, blank_response.status_code)
        self.assertDictEqual(
            blank_response.json(),
            {
                "email": ["This field is required."],
                "subject": ["This field is required."],
                "body": ["This field is required."],
            },
        )

        self.assertEqual(400, invalid_email_response.status_code)
        self.assertEqual(
            [CommentForm.epa_error_message], invalid_email_response.json()['email']
        )


class TestCommentCreateTemplate(TestCase):
    create_path_name = "feedback:comment_create"

    def setUp(self):
        self.factory = RequestFactory()
        self.template_name = "feedback/comment_create.html"
        self.form = CommentForm({})

    def test_comment_create_page(self):
        response = render(
            self.factory.get(reverse(self.create_path_name)),
            self.template_name,
            {"form": self.form},
        )
        page = html.fromstring(response.content)

        # Assert form has required inputs.
        self.assertTrue(page.xpath('//input[@id="id_email"]'))
        self.assertTrue(page.xpath('//textarea[@id="id_body"]'))
