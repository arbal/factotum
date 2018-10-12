from django.test import TestCase, override_settings
from dashboard.tests.loader import *
from dashboard.views.data_document import *
from lxml import html


@override_settings(ALLOWED_HOSTS=['testserver'])
class DataDocumentDetailTest(TestCase):
    fixtures = fixtures_standard

    def setUp(self):
        self.client.login(username='Karyn', password='specialP@55word')

    def test_extractedtext_update(self):
        self.assertTrue(ExtractedTextForm().fields['prod_name'],
                        'ExtractedTextForm must include prod_name')
        dd = DataDocument.objects.get(pk=7)
        et = ExtractedText.objects.filter(data_document=dd).get()
        response = self.client.post(f'/datadocument/{dd.pk}/',
                                    {'prod_name': 'zzz',
                                     'rev_num': '1',
                                     'doc_date': '01/01/2018',
                                     'save_extracted_text': ''})
        et.refresh_from_db()
        self.assertEqual(et.prod_name, 'zzz',
                         'The ExtractedText for DataDocument 7 should have a prod_name of "zzz"')

    def test_documenttype_update(self):
        self.assertTrue(DocumentTypeForm().fields['document_type'],
                        'DocumentTypeForm must include document_type')
        dd = DataDocument.objects.get(pk=7)
        response = self.client.post(f'/datadocument/{dd.pk}/',
                                    {'document_type': 2})
        dd.refresh_from_db()
        self.assertEqual(dd.document_type_id, 2,
                         'DataDocument 7 should have a final document_type_id of 2')
