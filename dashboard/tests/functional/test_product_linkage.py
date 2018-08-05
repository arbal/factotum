from django.test import TestCase, override_settings
from dashboard.tests.loader import *
from dashboard.views.product_curation import ProductLinkForm


@override_settings(ALLOWED_HOSTS=['testserver'])
class TestProductLinkage(TestCase):
    fixtures = fixtures_standard

    def setUp(self):
        self.client.login(username='Karyn', password='specialP@55word')

    def test_datatype_update(self):
        self.assertTrue(ProductLinkForm().fields['document_type'],
                            'ProductLinkForm must include a document_type select input')
        dd = DataDocument.objects.get(pk=155324)
        dd.document_type_id = 1
        dd.save()
        self.assertEqual(dd.document_type_id, 1,
                         'DataDocument 155324 must have a document_type_id of 1 for test to function')
        response = self.client.post(f'/link_product_form/155324',
                                    {'title': 'x',
                                     'manufacturer': '',
                                     'brand_name': '',
                                     'upc': 'none',
                                     'size': '',
                                     'color': '',
                                     'document_type': 2})
        dd.refresh_from_db()
        self.assertEqual(dd.document_type_id, 2,
                         'DataDocument 155324 should have a final document_type_id of 2')
