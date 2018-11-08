from django.test import TestCase, override_settings

from dashboard.tests.loader import *

class DataGroupTest(TestCase):

    def test_redirect_if_not_logged_in(self):
        response = self.client.get('/datagroups/')
        self.assertEqual(response.status_code, 302,
                                        "User should be redirected to login")
        self.assertEqual(response.url, '/login/?next=/datagroups/',
                                        "User should be sent to login page")

class DataGroupCodes(TestCase):

    fixtures = ['00_superuser.yaml','01_lookups.yaml',
                '02_datasource.yaml','07_script.yaml']

    def setUp(self):
        self.client.login(username='Karyn', password='specialP@55word')

    def test_code_table_present(self):
        response = self.client.get('/datasource/18/datagroup_new/')
        self.assertIn('<td>MS</td>',response.content.decode('utf-8'))
