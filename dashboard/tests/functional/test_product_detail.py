from lxml import html

from django.test import TestCase, override_settings

from dashboard.models import *
from dashboard.tests.loader import *
from dashboard.views.product_curation import ProductForm, ProductViewForm


@override_settings(ALLOWED_HOSTS=['testserver'])
class TestProductDetail(TestCase):
    fixtures = fixtures_standard

    def setUp(self):
        self.client.login(username='Karyn', password='specialP@55word')

    def test_product_delete(self):
        self.assertTrue(Product.objects.get(pk=11),
                         'Product 11 should exist')
        response = self.client.get(f'/product/delete/11/')
        self.assertFalse(Product.objects.filter(pk=11),
                         'Product 11 should have been deleted')

    def test_product_update(self):
        p = Product.objects.get(pk=11)
        response = self.client.post(f'/product/edit/11/',
                                    {'title': 'x',
                                     'manufacturer': '',
                                     'brand_name': '',
                                     'short_description': 'none',
                                     'long_description': 'none',
                                     'size': '',
                                     'color': '',
                                     'model_number': '2'})
        p.refresh_from_db()
        self.assertEqual(p.title, 'x',
                         'Product 11 should have the title "x"')


    def test_add_puc(self):
        p = Product.objects.get(pk=14)
        response = self.client.get(f'/product/{str(p.pk)}/').content.decode('utf8')
        response_html = html.fromstring(response)

        self.assertTrue(p.get_uber_puc() == None,
                        'Product should not have an assigned PUC')

        self.assertIn('Assign PUC',
                      response_html.xpath('string(//*[@id="button_assign_puc"]/text())'),
                      'There should be an Assign PUC button for this product')

        response = self.client.get(f'/product_puc/{str(p.pk)}/')

        self.assertNotIn('Currently assigned PUC:', response,
                                'Assigned PUC should not be visible')

        self.client.post(f'/product_puc/{str(p.pk)}/', {'puc': '96' })
        response = self.client.get(f'/product_puc/{str(p.pk)}/')

        self.assertIn(b'Currently assigned PUC:', response.content,
                                'Assigned PUC should be visible')
        # PUC is assigned....check that an edit will updated the record
        link = ProductToPUC.objects.get(PUC_id=96)
        # print(link.product_id)
        self.assertEqual(link.product_id, p.pk,
                            "PUC link should exist in table")
        self.client.post(f'/product_puc/{str(p.pk)}/', {'puc': '47' })
        link = ProductToPUC.objects.get(product=p)
        self.assertEqual(link.PUC_id, 47,
                            "PUC link should be updated in table")
        p.refresh_from_db()

        self.assertTrue(p.get_uber_puc() != None,
                        'Product should now have an assigned PUC')

        response = self.client.get('/product/{str(p.pk)}/').content.decode('utf8')
        response_html = html.fromstring(response)

        self.assertNotIn('Assign PUC',
                      response_html.xpath('string(//*[@id="button_assign_puc"]/text())'),
                      'There should not be an Assign PUC button for this product')
