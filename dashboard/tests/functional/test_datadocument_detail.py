from django.test import TestCase, override_settings
from django.test import Client

from dashboard.tests.loader import *
from dashboard.forms import *
from lxml import html
from factotum.settings import EXTRA 


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
        response = self.client.post(f'/save_ext/{dd.pk}/',
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
        response = self.client.post(f'/save_type/{dd.pk}/',
                                    {'document_type': 2})
        dd.refresh_from_db()
        self.assertEqual(dd.document_type_id, 2,
                         'DataDocument 7 should have a final document_type_id of 2')
    
    def test_absent_extracted_text(self):
        # Check every data document and confirm that its detail page loads,
        # with or without a detail formset
        for dd in DataDocument.objects.all():
            ddid = dd.id 
            resp = self.client.get('/datadocument/%s/' % ddid)
            self.assertEqual(resp.status_code, 200, 'The page must return a 200 status code')
            try:
                extracted_text = ExtractedText.objects.get(data_document=dd)
                self.assertContains(resp, '<h4>Extracted Text</h4>')
            except ExtractedText.DoesNotExist:
                self.assertNotContains(resp, '<h4>Extracted Text</h4>')


class TestDynamicDetailFormsets(TestCase):
    fixtures = fixtures_standard

    def setUp(self):
        self.c = Client()
        self.c.login(username='Karyn', password='specialP@55word')

    def test_fetch_extracted_records(self):
        ''' Confirm that each detail child object returned by the fetch_extracted_records
        function has the correct parent '''
        for et in ExtractedText.objects.all():
            #print('Fetching extracted child records from %s: %s ' % (et.pk , et))
            for ex_child in et.fetch_extracted_records():
                child_model = ex_child.__class__ # the fetch_extracted_records function returns different classes
                #print('    %s: %s' % (ex_child.__class__.__name__ , ex_child ))
                self.assertEqual(et.pk , child_model.objects.get(pk=ex_child.pk).extracted_text.pk,
                    'The ExtractedChemical object with the returned child pk should have the correct extracted_text parent')

    def test_every_extractedtext(self):
        ''''Loop through all the ExtractedText objects and confirm that the new
        create_detail_formset method returns forms based on the correct models
        '''
        for et in ExtractedText.objects.all():
            dd = et.data_document
            ParentForm, ChildForm = create_detail_formset(dd.data_group.type, EXTRA)
            extracted_text = et.pull_out_cp() #get CP if exists
            extracted_text_form = ParentForm(instance=extracted_text)
            child_formset = ChildForm(instance=extracted_text)
            # Compare the model of the child formset's QuerySet to the model
            # of the ExtractedText object's child objects
            dd_child_model  = get_extracted_models(dd.data_group.group_type.code)[1]
            childform_model = child_formset.__dict__.get('queryset').__dict__.get('model')
            self.assertEqual(dd_child_model, childform_model)


