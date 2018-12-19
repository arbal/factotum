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

    def test_absent_extracted_text(self):
        # Check every data document and confirm that its detail page loads,
        # with or without a detail formset
        for dd in DataDocument.objects.all():
            ddid = dd.id
            resp = self.client.get('/datadocument/%s/' % ddid)
            self.assertEqual(resp.status_code, 200, 'The page must return a 200 status code')
            try:
                extracted_text = ExtractedText.objects.get(data_document=dd)
            except ExtractedText.DoesNotExist:
                #print(dd.id)
                self.assertContains(resp, 'No Extracted Text exists for this Data Document')
            else:
                self.assertContains(resp, '<h4>Extracted Text</h4>')

    def test_script_links(self):
        doc = DataDocument.objects.first()
        response = self.client.get(f'/datadocument/{doc.pk}/')
        self.assertIn('Download Script',response.content.decode('utf-8'))
        self.assertIn('Extraction Script',response.content.decode('utf-8'))

    def test_product_card_location(self):
        response = self.client.get('/datadocument/179486/')
        html = response.content.decode('utf-8')
        e_idx = html.index('<h4>Extracted Text</h4>')
        p_idx = html.index('<h4 class="d-inline">Products</h4>')
        self.assertTrue(p_idx > e_idx, ('Product card should come after ' 
                                        'Extracted Text card'))

    def test_product_create_link(self):
        response = self.client.get('/datadocument/167497/')
        self.assertContains(response, '/link_product_form/167497/')
        data = {'title'        : ['New Product'],
                'upc'          : ['stub_1860'],
                'document_type': [1],
                'return_url'   : ['/datadocument/167497/']}
        response = self.client.post('/link_product_form/167497/', data=data)
        self.assertRedirects(response,'/datadocument/167497/')
        response = self.client.get(response.url)
        self.assertContains(response, 'New Product')


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

    def test_curated_chemical(self):
        ''''Confirm that if an ExtractedChemical record has been matched to DSSToxSubstance, the 
            DSSToxSubstance fields are displayed in the card
            This checks every data document.
        '''
        for et in ExtractedText.objects.all():
            dd = et.data_document
            ParentForm, ChildForm = create_detail_formset(dd.data_group.type)
            child_formset = ChildForm(instance=et)
            #print('Data doc %s , Group Type: %s ' % (dd.id, dd.data_group.type ))
            for form in child_formset.forms:
                if dd.data_group.type in ['CO','UN']:
                    ec = form.instance
                    if ec.true_cas is not None:
                        self.assertTrue( 'true_cas' in form.fields )
                    else:
                        self.assertFalse( 'true_cas' in form.fields )
                    if ec.sid is not None:
                        self.assertTrue( 'DTXSID' in form.fields )
                    else:
                        self.assertFalse( 'DTXSID' in form.fields )
                else:
                    self.assertFalse( 'true_cas' in form.fields )
            
