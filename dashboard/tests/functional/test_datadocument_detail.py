from lxml import html

from django.urls import reverse
from django.test import TestCase, override_settings
from django.core.exceptions import ObjectDoesNotExist

from dashboard.models import *
from dashboard.forms import *
from factotum.settings import EXTRA
from dashboard.tests.loader import *
from django.db.models import F, Min

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
                self.assertContains(resp, '<b>Extracted Text</b>')
    
    def test_curated_chemical(self):
        '''
        The correct values appear on the page for RawChem records 
        that have been matched to DSSToxLookup records, and
        the curated name and CAS appear in the sidebar navigation
        '''
        ddid = 7
        resp = self.client.get(f'/datadocument/%s/' % ddid)
        self.assertIn('href=/dsstox/DTXSID2021781/', resp.content.decode('utf-8'))

        # Any curated chemicals should also be linked to COMPTOX
        self.assertIn('https://comptox.epa.gov/dashboard/dsstoxdb/results?search=DTXSID2021781', resp.content.decode('utf-8'))
        
        page = html.fromstring(resp.content)
        # The raw chem name is different from the curated chem name,
        # so the right-side navigation link should NOT match the card
        # h3 element
        card_chemname = page.xpath('//*[@id="chem-4"]/div[2]/div[1]/h3')[0].text
        nav_chemname = page.xpath('//*[@id="chem-scrollspy"]/ul/li/a/p')[0].text
        self.assertFalse(card_chemname == nav_chemname,'The card and the scrollspy should show different chem names')
        
    def test_script_links(self):
        doc = DataDocument.objects.first()
        #response = self.client.get(f'/datadocument/{doc.pk}/')
        response = self.client.get(f'/datadocument/156051/')
        self.assertIn('Download Script',response.content.decode('utf-8'))
        self.assertIn('Extraction Script',response.content.decode('utf-8'))
        comptox = 'https://comptox.epa.gov/dashboard/dsstoxdb/results?search='
        self.assertContains(response, comptox)

    def test_product_card_location(self):
        response = self.client.get('/datadocument/179486/')
        html = response.content.decode('utf-8')
        e_idx = html.index('id="extracted-text-title"')
        p_idx = html.index('id="product-title"')
        self.assertTrue(p_idx < e_idx, ('Product card should come before ' 
                                        'Extracted Text card'))

    def test_product_create_link(self):
        response = self.client.get('/datadocument/167497/')
        self.assertContains(response, '/link_product_form/167497/')
        data = {'title'        : ['New Product'],
                'upc'          : ['stub_9860'],
                'document_type': [''],
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
                'document_type': [''],
                'return_url'   : ['/datadocument/245401/']}
        response = self.client.post('/link_product_form/245401/', data=data)
        self.assertRedirects(response,'/datadocument/245401/')
        response = self.client.get(response.url)
        new_product = Product.objects.get(upc='stub_9100')
        self.assertContains(response, f'product/%s' % new_product.id )

        # Add another new Product with the same title
        data = {'title'        : ['Product Title'],
                'upc'          : ['stub_9101'],
                'document_type': [''],
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
        self.assertFalse(doc.is_extracted, ("This document is matched "
                                                    "but not extracted"))
        data = {'hhe_report_number': ['47']}
        response = self.client.post('/extractedtext/edit/354784/', data=data,
                                                            follow=True)
        doc.refresh_from_db()
        self.assertTrue(doc.is_extracted, "This document should be extracted ")
        page = html.fromstring(response.content)
        
        hhe_no = page.xpath('//*[@id="id_hhe_report_number"]')[0].text
        self.assertIn('47', hhe_no)

    def test_delete(self):
        '''Checks if data document is deleted after POSTing to
        /datadocument/delete/<pk>
        '''
        post_uri = "/datadocument/delete/"
        pk = 354784
        doc_exists = lambda: DataDocument.objects.filter(pk=pk).exists()
        self.assertTrue(doc_exists(), "Document does not exist prior to delete attempt.")
        self.client.post(post_uri + str(pk) + "/")
        self.assertTrue(not doc_exists(), "Document still exists after delete attempt.")

    def test_ingredient_rank(self):
        response = self.client.get('/datadocument/254643/')
        html = response.content.decode('utf-8')
        first_idx = html.index('name="rawchem-0-ingredient_rank" value="1"')
        second_idx = html.index('name="rawchem-1-ingredient_rank" value="2"')
        self.assertTrue(second_idx > first_idx, ('Ingredient rank 1 comes before ' 
                                        'Ingredient rank 2'))


    def test_title_ellipsis(self):
        '''Check that DataDocument title gets truncated'''
        trunc_length = 45
        doc = (DataDocument
            .objects
            .filter(title__iregex=('.{%i,}' % (trunc_length + 1)))
            .first())
        self.assertIsNotNone(doc, ('No DataDocument found with a title greater'
                                   ' than %i characters.') % trunc_length)
        response = self.client.get('/datadocument/%i/' % doc.id)
        response_html = html.fromstring(response.content)
        trunc_title = doc.title[:trunc_length - 1] + '…'
        html_title = response_html.xpath('//*[@id="title"]/h1')[0].text
        self.assertEqual(trunc_title, html_title, 'DataDocument title not truncated.')

    def test_chemname_ellipsis(self):
        '''Check that DataDocument chemical names get truncated'''
        trunc_length = 45
        trunc_side_length = 18
        doc = (DataDocument
            .objects
            .filter(extractedtext__rawchem__raw_chem_name__iregex=('.{%i,}' % (trunc_length + 1)))
            .prefetch_related('extractedtext__rawchem')
            .first())
        rc = (doc.extractedtext.rawchem
            .filter(raw_chem_name__iregex=('.{%i,}' % (trunc_length + 1)))
            .first())
        self.assertIsNotNone(doc, ('No DataDocument found with a chemical name greater'
                                   ' than %i characters.') % trunc_length)
        response = self.client.get('/datadocument/%i/' % doc.id)
        response_html = html.fromstring(response.content)
        trunc_rc_name = rc.raw_chem_name[:trunc_length - 1] + '…'
        trunc_side_rc_name = rc.raw_chem_name[:trunc_side_length - 1] + '…'
        path = '//*[@id="chem-%i"]/div/div[1]/h3' % rc.id
        side_path = '//*[@id="chem-scrollspy"]/ul/li/a[@href=\'#chem-%i\']/p' % rc.id
        html_rc_name = response_html.xpath(path)[0].text
        html_side_rc_name = response_html.xpath(side_path)[0].text
        self.assertHTMLEqual(trunc_rc_name, html_rc_name, 'Long DataDocument chemical names not truncated.')
        self.assertHTMLEqual(trunc_side_rc_name, html_side_rc_name, 'Long DataDocument chemical names not truncated in sidebar.')


class TestDynamicDetailFormsets(TestCase):
    fixtures = fixtures_standard

    def setUp(self):
        self.client.login(username='Karyn', password='specialP@55word')

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
                    self.assertEqual(type(extsub) , ExtractedCPCat)
                elif doc.data_group.group_type.code=='HH':
                    self.assertEqual(type(extsub) , ExtractedHHDoc)
                else:
                    self.assertEqual(type(extsub) , ExtractedText)
            except ObjectDoesNotExist:
                pass


    def test_every_extractedtext(self):
        ''''Loop through all the ExtractedText objects and confirm that the new
        create_detail_formset method returns forms based on the correct models
        '''
        for et in ExtractedText.objects.all():
            dd = et.data_document
            ParentForm, ChildForm = create_detail_formset(dd, EXTRA)
            child_formset = ChildForm(instance=et)
            # Compare the model of the child formset's QuerySet to the model
            # of the ExtractedText object's child objects
            dd_child_model  = get_extracted_models(dd.data_group.group_type.code)[1]
            childform_model = child_formset.__dict__.get('queryset').__dict__.get('model')
            self.assertEqual(dd_child_model, childform_model)

      
    def test_num_forms(self):
        ''''Assure that the number of child forms is appropriate for the group type.
        '''
        for code, model in datadocument_models.items():
            if DataDocument.objects.filter(
                                data_group__group_type__code=code,
                                extractedtext__isnull=False
            ):

                doc = DataDocument.objects.filter(
                                    data_group__group_type__code=code,
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


    def test_listpresence_tags_form(self):
        ''''Assure that the list presence keywords appear for correct doc types and tags save
        '''
        for code, model in datadocument_models.items():
            if DataDocument.objects.filter(

                                data_group__group_type__code=code,
                                extractedtext__isnull=False
            ):
                doc = DataDocument.objects.filter(
                                    data_group__group_type__code=code,

                                    extractedtext__isnull=False
                ).first()
                response = self.client.get(reverse('data_document',kwargs={'pk': doc.pk}))
                response_html = html.fromstring(response.content.decode('utf8'))
                if code=='CP':
                    self.assertTrue(response_html.xpath('boolean(//*[@id="id_tags"])'),
                              'Tag input should exist for Chemical Presence doc type')
                    elpt_count = ExtractedListPresenceTag.objects.count()
                    # seed data contains 2 tags for the 50 objects in this document
                    elp2t_count = ExtractedListPresenceToTag.objects.count()
                    # This post should preseve the 2 existing tags and add 2 more
                    req = self.client.post(path=reverse('save_list_presence_tag_form',kwargs={'pk': doc.pk}),
                                           data={'tags':'after_shave,agrochemical,flavor,slimicide'})
                    # Total number of tags should not have changed
                    self.assertEqual(ExtractedListPresenceTag.objects.count(), elpt_count)
                    # But the tagged relationships should have increased by 2 * the number of list presence objects
                    self.assertEqual(ExtractedListPresenceToTag.objects.count(), elp2t_count + (2 * doc.extractedtext.rawchem.select_subclasses('extractedlistpresence').count()))
                else:
                    self.assertFalse(response_html.xpath('boolean(//*[@id="id_tags"])'),

                              'Tag input should only exist for Chemical Presence doc type')



    def test_listpresence_tag_curation(self):
        ''''Assure that the list presence keyword link appears in nav,
            and correct docs are listed on the page
        '''
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'href="' + reverse('list_presence_tag_curation') + '"')

        response = self.client.get(reverse('list_presence_tag_curation'))
        list_presence_ids = ExtractedListPresenceToTag.objects.values_list('content_object_id',flat=True)
        documents = DataDocument.objects\
            .annotate(code = F('data_group__group_type__code'))\
            .annotate(list_presence_id=Min('extractedtext__rawchem'))
        for document in documents:
            if document.code != 'CP' or document.list_presence_id in list_presence_ids:
                self.assertNotContains(response, 'href="' + reverse('data_document', kwargs={'pk': document.pk}) + '"')
            elif document.list_presence_id not in list_presence_ids:
                self.assertContains(response, 'href="' + reverse('data_document', kwargs={'pk': document.pk}) + '"')

