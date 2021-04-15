from unittest import skip

from bs4 import BeautifulSoup

from django.test import TestCase, override_settings


@skip("No longer supported in OY5")
@override_settings(ROOT_URLCONF="factotum.urls.api")
class TestOpenapi(TestCase):
    def test_title(self):
        response = self.client.get("/")
        soup = BeautifulSoup(response.content, "html.parser")

        self.assertEqual(soup.title.string, "Factotum API")
