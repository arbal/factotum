from django.test import TestCase, override_settings
from dashboard.tests.loader import *
from lxml import html
from django.urls import reverse
from dashboard.models import PUC, PUCTag, Product, ProductToTag

@override_settings(ALLOWED_HOSTS=['testserver'])
class TestProductPucTags(TestCase):
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


