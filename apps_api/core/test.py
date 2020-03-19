from rest_framework.test import APITestCase

from dashboard.tests.loader import fixtures_standard


class TestCase(APITestCase):
    fixtures = fixtures_standard

    def __init__(self, methodName="runTest"):
        super().__init__(methodName)

    def get(self, *args, **kwargs):
        """ Shortcut to get """
        with self.settings(ROOT_URLCONF="factotum.urls.api"):
            return self.client.get(*args, **kwargs).data
