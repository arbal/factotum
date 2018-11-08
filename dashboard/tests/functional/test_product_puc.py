from django.test import TestCase, override_settings
from dashboard.tests.loader import *
from lxml import html
from django.urls import reverse
from dashboard.models import PUC, PUCTag, Product, ProductToTag

@override_settings(ALLOWED_HOSTS=['testserver'])
class TestProductPuc(TestCase):
    fixtures = fixtures_standard

    def setUp(self):
        self.client.login(username='Karyn', password='specialP@55word')

    def test_admin_puc_tag_column_exists(self):
        self.assertEqual(PUCTag.objects.count(), 19, "There should be 19 PUC tags defined in the system.")
        response_url = reverse('admin:dashboard_puc_changelist')
        response = self.client.get(response_url)
        response_html = html.fromstring(response.content.decode('utf8'))
        self.assertIn('Tag list', response_html.xpath('string(/html/body/div[1]/div[3]/div/div/form/div[2]/table/thead/tr/th[3]/div[1])'),
                      'The column Tag List should exist on the PUC admin table')
        self.assertIn('aerosol', response_html.xpath('string(/html/body/div[1]/div[3]/div/div/form/div[2]/table/tbody/tr[2]/td[2])'),
                      'The tag aerosol should exist in the tag list column for PUC 1')

    def test_admin_puc_change(self):
        puc = PUC.objects.get(pk=1)
        puc_response_url = reverse('admin:dashboard_puc_change', args=(puc.pk,))
        response = self.client.get(puc_response_url)
        puc_response_html = html.fromstring(response.content.decode('utf8'))
        self.assertIn('selected',
                      puc_response_html.xpath('string(//*[@id="id_tags"]/li[@data-tag-name="aerosol"]/@class)'),
                      'The tag aerosol should exist and be selected')
        self.assertNotIn('selected',
                         puc_response_html.xpath('string(//*[@id="id_tags"]/li[@data-tag-name="cartridge"]/@class)'),
                         'The tag cartridge should exist but not be selected')
        p = Product.objects.get(pk=11)
        product_response_url = reverse('product_detail', kwargs={'pk': p.pk})
        product_response = self.client.get(product_response_url)
        product_response_html = html.fromstring(product_response.content.decode('utf8'))
        self.assertIn('selected',
                      product_response_html.xpath('string(//*[@id="id_tags"]/li[@data-tag-name="aerosol"]/@class)'),
                      'The tag aerosol should exist and be selected for this product')
        self.assertFalse(product_response_html.xpath('string(//*[@id="id_tags"]/li[@data-tag-name="cartridge"]/@class)'),
                         'The tag cartridge should not exist for this product')
        response = self.client.post(puc_response_url,
                                    {'gen_cat': 'Arts and crafts/Office supplies',
                                     'prod_fam': 'body paint',
                                     'brand_name': '',
                                     'description': 'body paints, markers, glitters, play cosmetics, and halloween cosmetics',
                                     'tags': 'aerosol, foamspray, gel, paste, powder|spray, cartridge'})
        product_response = self.client.get(product_response_url)
        product_response_html = html.fromstring(product_response.content.decode('utf8'))
        self.assertTrue(product_response_html.xpath('string(//*[@id="id_tags"]/li[@data-tag-name="cartridge"]/@class)'),
                         'The tag cartridge should now exist for this product')
        response = self.client.post(product_response_url,
                                    {'tags': 'powder|spray, cartridge'})
        product_response = self.client.get(product_response_url)
        product_response_html = html.fromstring(product_response.content.decode('utf8'))
        self.assertNotIn('selected',
                      product_response_html.xpath('string(//*[@id="id_tags"]/li[@data-tag-name="aerosol"]/@class)'),
                      'The tag aerosol should exist but not be selected for this product')
        self.assertIn('selected',
                         product_response_html.xpath('string(//*[@id="id_tags"]/li[@data-tag-name="cartridge"]/@class)'),
                         'The tag cartridge should exist but not be selected for this product')


    def test_bulk_product_puc_ui(self):
        product_response_url = reverse('bulk_product_puc')
        product_response = self.client.get(product_response_url)
        product_response_html = html.fromstring(product_response.content.decode('utf8'))
        self.assertIn('Locate products to associate with PUCs using the Search bar above',
                      product_response_html.xpath('string(/)'),
                      'The form should not display without search criteria')
        product_response = self.client.get(product_response_url + '?q=ewedwefwefds')
        product_response_html = html.fromstring(product_response.content.decode('utf8'))
        self.assertIn('Locate products to associate with PUCs using the Search bar above.',
                      product_response_html.xpath('string(/)'),
                      'The form should not display if no products are returned')
        product_response = self.client.get(product_response_url + '?q=bayer')
        product_response_html = html.fromstring(product_response.content.decode('utf8'))
        self.assertIn('Product Title',
                      product_response_html.xpath('string(//*[@id="products"]/thead/tr/th[2]/text())'),
                      'The DataTable should display the matching products on successful search')

    def test_bulk_product_puc_post(self):
        product_response_url = reverse('bulk_product_puc')
        response = self.client.post(product_response_url,
                                    {'puc': '1',
                                     'id_pks': '11,150,151,152'})
        # Note that product 11 already has PUC 1 linked to it in the seed data. Including it in this
        # test set is a test against the edge case wherein a product with a manually assigned PUC
        # somehow makes it into the batch assignment process
        product = Product.objects.get(pk=11)
        puc = PUC.objects.get(pk=1)
        pucs  = product.producttopuc_set
        self.assertEqual(product.get_uber_puc(), puc, "Product 11 should now be assigned to PUC 1" )

    def test_bulk_product_puc_post_without_products(self):
        product_response_url = reverse('bulk_product_puc')
        response = self.client.post(product_response_url,
                                    {'puc': '1'})
        self.assertEqual(response.status_code, 200, 
            "The request should return a valid response even without any Products" )

