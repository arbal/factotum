from lxml import html

from django.test import Client
from django.urls import reverse
from django.test import TestCase, override_settings
from django.core.exceptions import ObjectDoesNotExist

from dashboard.forms import *
from factotum.settings import EXTRA
from dashboard.tests.loader import *


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
                self.assertContains(resp, '<h4>Extracted Text')

    def test_script_links(self):
        doc = DataDocument.objects.first()
        #response = self.client.get(f'/datadocument/{doc.pk}/')
        response = self.client.get(f'/datadocument/179486/')
        self.assertIn('Download Script',response.content.decode('utf-8'))
        self.assertIn('Extraction Script',response.content.decode('utf-8'))

    def test_product_card_location(self):
        response = self.client.get('/datadocument/179486/')
        html = response.content.decode('utf-8')
        e_idx = html.index('<h4>Extracted Text')
        p_idx = html.index('<h4 class="d-inline">Products')
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

    def test_product_title_duplication(self):
        response = self.client.get('/datadocument/245401/')
        self.assertContains(response, '/link_product_form/245401/')
        # Add a new Product
        data = {'title'        : ['Product Title'],
                'upc'          : ['stub_9100'],
                'document_type': [1],
                'return_url'   : ['/datadocument/245401/']}
        response = self.client.post('/link_product_form/245401/', data=data)
        self.assertRedirects(response,'/datadocument/245401/')
        response = self.client.get(response.url)
        new_product = Product.objects.get(upc='stub_9100')
        self.assertContains(response, f'product/%s' % new_product.id )

        # Add another new Product with the same title
        data = {'title'        : ['Product Title'],
                'upc'          : ['stub_9101'],
                'document_type': [1],
                'return_url'   : ['/datadocument/245401/']}
        response = self.client.post('/link_product_form/245401/', data=data)
        self.assertRedirects(response,'/datadocument/245401/')
        response = self.client.get(response.url)
        new_product = Product.objects.get(upc='stub_9101')
        self.assertContains(response, f'product/%s' % new_product.id )

    def test_add_extracted(self):
        '''Check that the user has the ability to create an extracted record
        when the document doesn't yet have an extracted record for data 
        group types 'CP' and 'HH'
        '''
        doc = DataDocument.objects.get(pk=354784)
        self.assertFalse(doc.extracted, ("This document is matched "
                                                    "but not extracted"))
        data = {'hhe_report_number': ['47']}
        response = self.client.post('/extractedtext/edit/354784/', data=data,
                                                            follow=True)
        doc = DataDocument.objects.get(pk=354784)
        self.assertTrue(doc.extracted, "This document is not extracted ")
        page = html.fromstring(response.content)
        hhe_no = page.xpath('//dd[contains(@class, "hh-report-no")]')[0].text
        self.assertIn('47', hhe_no)


class TestDynamicDetailFormsets(TestCase):
    fixtures = fixtures_standard

    def setUp(self):

        self.client.login(username='Karyn', password='specialP@55word')

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

    def test_extractedsubclasses(self):
        ''' Confirm that the inheritance manager is returning appropriate
            subclass objects and ExtractedText base class objects 
         '''
        for doc in DataDocument.objects.all():
            try:
                extsub = ExtractedText.objects.get_subclass(data_document=doc)
                # A document with the CP data group type should be linked to 
                # ExtractedCPCat objects
                if doc.data_group.group_type.code=='CP':
                    #print(f'%s %s %s' % (doc.id, extsub, type(extsub)))
                    self.assertEqual(type(extsub) , ExtractedCPCat)
                elif doc.data_group.group_type.code=='HH':
                    self.assertEqual(type(extsub) , ExtractedHHDoc)
                else:
                    self.assertEqual(type(extsub) , ExtractedText)
            except ObjectDoesNotExist:
                pass
                #print('No extracted text for data document %s' % doc.id)


    def test_every_extractedtext(self):
        ''''Loop through all the ExtractedText objects and confirm that the new
        create_detail_formset method returns forms based on the correct models
        '''
        for et in ExtractedText.objects.all():
            dd = et.data_document
            ParentForm, ChildForm = create_detail_formset(dd, EXTRA)
            extracted_text_form = ParentForm(instance=et)
            child_formset = ChildForm(instance=et)
            # Compare the model of the child formset's QuerySet to the model
            # of the ExtractedText object's child objects
            dd_child_model  = get_extracted_models(dd.data_group.group_type.code)[1]
            childform_model = child_formset.__dict__.get('queryset').__dict__.get('model')
            self.assertEqual(dd_child_model, childform_model)

    def test_curated_chemical(self):
        ''''Confirm that if an ExtractedChemical record has been matched to DSSToxLookup, the 
            DSSToxLookup fields are displayed in the card
            This checks every data document.
        '''
        for et in ExtractedText.objects.all():
            dd = et.data_document
            ParentForm, ChildForm = create_detail_formset(dd)
            child_formset = ChildForm(instance=et)
            #print('Data doc %s , Group Type: %s ' % (dd.id, dd.data_group.type ))
            for form in child_formset.forms:
                if dd.data_group.type in ['CO','UN']:
                    ec = form.instance
                    if ec.dsstox is not None:
                        self.assertTrue( 'true_cas' in form.fields )
                        self.assertTrue( 'SID' in form.fields )
                    else:
                        self.assertFalse( 'true_cas' in form.fields )
                        self.assertFalse( 'SID' in form.fields )
                else:
                    self.assertFalse( 'true_cas' in form.fields )
            
    def test_num_forms(self):
        ''''Assure that the number of child forms is appropriate for the group
        type.
        '''
        group_models = {
                        'CO': ExtractedChemical,
                        'FU': ExtractedFunctionalUse,
                        'HP': ExtractedHabitsAndPractices,
                        'CP': ExtractedListPresence,
                        'HH': ExtractedHHRec
        }
        for code, model in group_models.items():
            if DataDocument.objects.filter(
                                document_type__group_type__code=code,
                                extractedtext__isnull=False
            ):

                doc = DataDocument.objects.filter(
                                    document_type__group_type__code=code,
                                    extractedtext__isnull=False
                ).first()
                response = self.client.get(
                                    reverse('data_document',kwargs={'pk': doc.pk})
                )
                num_forms = response.context['detail_formset'].total_form_count()
                children = model.objects.filter(
                                    extracted_text=doc.extractedtext
                ).count()

                if doc.detail_page_editable:
                    error = (f'{model.__module__} should have one more forms'
                                                                ' than instances')
                    self.assertEqual(num_forms, children + 1, error)
                else:
                    error = (f'{model.__module__} should have the same number'
                                                        ' of forms as instances')
                    self.assertEqual(num_forms, children, error)


