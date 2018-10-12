from django.test import TestCase, override_settings

from dashboard.tests.loader import *

class DataGroupTest(TestCase):

    def test_redirect_if_not_logged_in(self):
        response = self.client.get('/datagroups/')
        self.assertEqual(response.status_code, 302,
                                        "User should be redirected to login")
        self.assertEqual(response.url, '/login/?next=/datagroups/',
                                        "User should be sent to login page")
