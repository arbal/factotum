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
        dd.document_type = None
        dd.save()
        self.assertEqual(dd.document_type_id, None,
                         'DataDocument 155324 must have a document_type_id of NULL for test to function')
        response = self.client.post(f'/link_product_form/155324/',
                                    {'title': 'x',
                                     'manufacturer': '',
                                     'brand_name': '',
                                     'upc': 'none',
                                     'size': '',
                                     'color': '',
                                     'document_type': 2,
                                     'return_url': 'required'})
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

    def test_bulk_create_products(self):
        # DataGroup 19 is a Composition dg with unlinked products
        dg = DataGroup.objects.get(pk=19)
        response = self.client.get(f'/datagroup/19/')
        unlinked = dg.datadocument_set.filter(products__isnull=True).count()
        self.assertEqual(response.context['bulk_product_count'], unlinked,
                'Not all DataDocuments linked to Product, bulk_create needed')
        response = self.client.post(f'/datagroup/19/',{'bulk':unlinked})
        self.assertEqual(response.context['bulk'], 0,
                'Product linked to all DataDocuments, no bulk_create needed.')
        # pick documents and check the attributes of their now-related products
        # 1: check a case where the ExtractedText record had a prod_name to offer
        ets = ExtractedText.objects.filter(data_document__data_group=dg)
        et = ets.filter(prod_name__isnull=False).first()
        doc = DataDocument.objects.get(pk=et.data_document_id)
        product = ProductDocument.objects.get(document=doc).product
        self.assertEqual(product.title, et.prod_name,
                                        'Title should be taken from ExtractedText.prod_name in bulk_create')
        # 2: check a case where ExtractedText.prod_name is None
        et = ets.filter(prod_name__isnull=True).first()
        doc = DataDocument.objects.get(pk=et.data_document_id)
        product = ProductDocument.objects.get(document=doc).product
        self.assertEqual(product.title, '%s stub' % doc.title ,
                                        ('Title should be taken from the DataDocument.title in bulk_create,'
                                        'with "stub" appended') )
        # 3: check a case where the ExtractedText doesn't exist
        # Data Group 6 has 2 docs that are linked to Product and ExtractedText records
        dg = DataGroup.objects.get(pk=6)
        docs = DataDocument.objects.filter(data_group=dg)
        doc_list = docs.values_list('id')
        # delete the ExtractedText links and recreate them via the bulk request
        ExtractedText.objects.filter(data_document_id__in=doc_list).delete()
        # delete the ProductDocument links and recreate them via the bulk request
        ProductDocument.objects.filter(document_id__in=doc_list).delete()
        response = self.client.get(f'/datagroup/6/')
        self.assertEqual(response.context['bulk_product_count'], 2,
                'Not all DataDocuments linked to Product, bulk_create needed')
        response = self.client.post(f'/datagroup/6/',{'bulk':1})
        self.assertEqual(response.context['bulk'], 0,
                'Product linked to all DataDocuments, no bulk_create needed.')
        # check the titles of the newly-created products
        # they should be based on the document title
        doc = docs.first()
        prod = Product.objects.filter(documents__in=[doc]).first()
        self.assertEqual('%s stub' % doc.title, prod.title,
                'Product and DataDocument titles should be the same.')
        

