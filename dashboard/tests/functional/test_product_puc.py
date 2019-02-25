from django.test import TestCase, override_settings
from dashboard.tests.loader import *
from lxml import html
from django.urls import reverse
from dashboard.models import PUC, PUCTag, PUCToTag, Product, ProductToTag

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
        response = self.client.get(reverse('admin:dashboard_puctotag_changelist'))
        response_html = html.fromstring(response.content.decode('utf8'))
        # import pdb; pdb.set_trace()
        tag_col = response_html.xpath('//th[contains(@class, "column-tag")]/div/a')[0].text
        self.assertEqual('Tag', tag_col, "Tag should be a column in the table!")
        tag_filter = response_html.xpath('//div[contains(@id, "changelist-filter")]/h3')[0].text
        self.assertEqual(tag_filter, ' By tag ', "Filter by tag!")


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
        assumed = product_response_html.xpath('//button[contains(@class, "assumed")]')
        self.assertEqual(len(assumed), 2, "There should be 2 assumed attributes")
        self.assertEqual([ass.text for ass in assumed], ['gel', 'powder|spray'],
                            "Assumed attributes are incorrect.")


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

    def test_bulk_product_tag_post(self):
        product_response_url = reverse('bulk_product_tag')
        response = self.client.post(product_response_url,
                                    {'puc': 1,
                                     'tag': '9',
                                     'id_pks': '11,1845',
                                     'save':'save'})

        self.assertIn('The &quot;paste&quot; Attribute was assigned to 2 Product(s)', response.content.decode('utf-8'),
                      'The "aerosol" tag message should be displayed in the response')
        self.assertIn('Along with the assumed tags: gel | powder|spray', response.content.decode('utf-8'),
                      'The assumed tags should be displayed in the response')
        product = Product.objects.get(pk=11)
        tag_count  = product.producttotag_set.count()
        self.assertEqual(tag_count, 5, "Product 11 should now be assigned to 5 Tags" )

    def test_bulk_product_tag_post_without_products(self):
        product_response_url = reverse('bulk_product_tag')
        response = self.client.post(product_response_url,
                                    {'puc': 1, 'tag': '1'})
        self.assertEqual(response.status_code, 200,
            "The request should return a valid response even without any Products" )

    def test_bulk_product_tag_filter(self):
        puc_attrs = PUCToTag.objects.filter(content_object_id=1) 
        assumed_attrs = [attr.tag.name for attr in puc_attrs.filter(assumed=True)]
        self.assertEqual(['gel', 'powder|spray'], assumed_attrs)
        product_response_url = reverse('bulk_product_tag')
        response = self.client.post(product_response_url,
                                    {'puc': 1})
        response_html = html.fromstring(response.content.decode('utf8'))
        select = response_html.xpath('//select[contains(@id, "id_tag")]/option')
        texts = [x.text for x in select]
        for attr in assumed_attrs:
            self.assertNotIn(attr, texts, "assumed attributes shouldn't be here")
        # import pdb; pdb.set_trace()
 