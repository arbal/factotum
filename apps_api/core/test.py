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

    def post(self, *args, authenticate=True, **kwargs):
        """ Shortcut to post """
        with self.settings(ROOT_URLCONF="factotum.urls.api"):
            if authenticate:
                token = self.client.post(
                    "/token/",
                    data={
                        "data": {
                            "type": "token",
                            "attributes": {
                                "username": "karyn",
                                "password": "specialP@55word",
                            },
                        }
                    },
                ).data.get("token")
                self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
            return self.client.post(*args, **kwargs)
