from django.test import TestCase, override_settings
from dashboard.tests.loader import *
from dashboard.views.product_curation import ProductForm, ProductViewForm


@override_settings(ALLOWED_HOSTS=['testserver'])
class TestProductDetail(TestCase):
    fixtures = fixtures_standard

    def setUp(self):
        self.client.login(username='Karyn', password='specialP@55word')

    def test_product_update(self):
        self.assertFalse('title' in ProductViewForm().fields,
                            'ProductViewForm should not include the product title')
        self.assertTrue(ProductForm().fields['title'],
                         'ProductViewForm should include the product title')
        response = self.client.post(f'/product/edit/11',
                                    {'title': 'x',
                                     'manufacturer': '',
                                     'brand_name': '',
                                     'short_description': 'none',
                                     'long_description': 'none',
                                     'size': '',
                                     'color': '',
                                     'model_number': '2'})
        p = Product.objects.get(pk=11)
        self.assertEqual(p.title, 'x',
                         'Product 11 should have the title "x"')


