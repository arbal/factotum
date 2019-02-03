from lxml import html

from django.test import TestCase, override_settings

from dashboard.models import *
from dashboard.tests.loader import *
from dashboard.views.product_curation import ProductForm, ProductTagForm


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

        response = self.client.get(f'/product_puc/{str(p.pk)}/').content.decode('utf8')

        self.assertNotIn('Currently assigned PUC:', response,
                                'Assigned PUC should not be visible')
        # Assign PUC 96
        self.client.post(f'/product_puc/{str(p.pk)}/', {'puc': '96' })

        response = self.client.get(f'/product_puc/{str(p.pk)}/?').content.decode('utf8')
        self.assertIn('Currently assigned PUC:', response,
                                'Assigned PUC should be visible')

        # PUC is assigned....check that an edit will updated the record
        self.assertTrue(ProductToPUC.objects.filter(puc_id=96, product_id=p.pk).exists(),
                            "PUC link should exist in table")

        # Assign PUC 47, check that it replaces 96
        self.client.post(f'/product_puc/{str(p.pk)}/', {'puc': '47' })
        self.assertTrue(ProductToPUC.objects.filter(product=p).filter(puc_id=47).exists(),
                            "PUC link should be updated in table")
        p.refresh_from_db()
        self.assertTrue(p.get_uber_puc() != None,
                        'Product should now have an assigned PUC')

        response = self.client.get('/product/{str(p.pk)}/').content.decode('utf8')
        response_html = html.fromstring(response)

        self.assertNotIn('Assign PUC',
                      response_html.xpath('string(//*[@id="button_assign_puc"]/text())'),
                      'There should not be an Assign PUC button for this product')

    def test_document_table_order(self):
        p = Product.objects.get(pk=1850)
        one = p.datadocument_set.all()[0]
        two = p.datadocument_set.all()[1]
        self.assertTrue(one.created_at < two.created_at,
                        f'Doc |{one.pk}| needs to have been created first')
        t1 = one.title
        t2 = two.title
        response = self.client.get('/product/1850/')
        # see that the more recent document is on the top of the table based
        # on the index of where the title falls in the output
        older_doc_index = response.content.decode('utf8').index(t1)
        newer_doc_index = response.content.decode('utf8').index(t2)
        self.assertTrue(older_doc_index > newer_doc_index,('Most recent doc'
                                            ' should be on top of the table!'))

    def test_puc_not_specified(self):
        '''Product 1840 is associated with a PUC that has no prod_fam or
        prod_type specified.
        '''
        response = self.client.get('/product/1840/')
        count = response.content.decode('utf-8').count('not specified')
        self.assertEqual(count,2, ('Both prod_fam and prod_type should'
                                    'not be specified.'))
