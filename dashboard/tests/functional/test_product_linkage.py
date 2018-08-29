from django.test import TestCase, override_settings
from dashboard.tests.loader import *
from dashboard.views.product_curation import ProductLinkForm
from lxml import html


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
        response = self.client.post(f'/link_product_form/155324/',
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

    def test_datatype_options(self):
        # retrieve a sample datadocument
        dd = DataDocument.objects.get(pk=129298)

        # configure its datagroup to be of group type "composition"
        dg = DataGroup.objects.get(pk=dd.data_group_id)
        dg.group_type_id = 2
        dg.save()

        response = self.client.get(f'/link_product_form/{str(dd.pk)}/').content.decode('utf8')
        response_html = html.fromstring(response)

        self.assertTrue(response_html.xpath('string(//*[@id="id_document_type"]/option[@value="5"])'),
                      'Document_type_id 5 should be an option when the datagroup type is composition.')

        self.assertFalse(response_html.xpath('string(//*[@id="id_document_type"]/option[@value="6"])'),
                      'Document_type_id 6 should NOT be an option when the datagroup type is composition.')
