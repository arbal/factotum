from lxml import html

from django.test import TestCase, override_settings

from dashboard.models import *
from dashboard.tests.loader import *


@override_settings(ALLOWED_HOSTS=['testserver'])
class TestPUCDetail(TestCase):
    fixtures = fixtures_standard

    def setUp(self):
        self.client.login(username='Karyn', password='specialP@55word')

    def test_puc_not_specified(self):
        response = self.client.get('/puc/20/').content.decode('utf8')
        response_html = html.fromstring(response)
        self.assertTrue(response_html.xpath('string(//*[@id="assumed_attributes"][count(button) = 2])'),
                        'Two assumed tags should exist for this PUC.')
        self.assertTrue(response_html.xpath('string(//*[@id="allowed_attributes"][count(button)=7])'),
                        'Seven allowed tags should exist for this PUC.')


