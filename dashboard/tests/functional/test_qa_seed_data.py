from django.test import Client
from dashboard.tests.loader import *
from django.test import TestCase, override_settings, RequestFactory
from dashboard.models import DataDocument, Script, ExtractedText, ExtractedChemical, QAGroup

@override_settings(ALLOWED_HOSTS=['testserver'])
class TestQaPage(TestCase):
    fixtures = fixtures_standard

    def setUp(self):
        self.factory = RequestFactory()
        self.client.login(username='Karyn', password='specialP@55word')


    def test_qa_begin(self):
        """
        Check that starting the QA process flips the variable on the Script
        """
        self.assertFalse(Script.objects.get(pk=5).qa_begun,
                    'The Script should have qa_begun of False at the beginning')
        response = self.client.get('/qa/extractionscript/5/')
        self.assertTrue(Script.objects.get(pk=5).qa_begun,
                    'qa_begun should now be true')
    
    def test_new_qa_group_urls(self):
        # Begin from the QA index page
        response = self.client.get(f'/qa/')
        self.assertIn(f"/qa/extractionscript/15/'> Begin QA".encode() , response.content)
        # Script 15 has one ExtractedText object
        pk = 15
        response = self.client.get(f'/qa/extractionscript/{pk}/')
        et = ExtractedText.objects.filter(extraction_script = pk).first()
        self.assertIn(f'/qa/extractedtext/{et.pk}/'.encode() , response.content)
        # After opening the URL, the following should be true:
        # One new QA group should be created
        group_count = QAGroup.objects.filter(extraction_script_id = pk).count()
        self.assertTrue( group_count == 1)
        # The ExtractionScript's qa_begun property should be set to True
        self.assertTrue( Script.objects.get(pk=15).qa_begun )
        # The ExtractedText object should be assigned to the QA Group
        group_pk = QAGroup.objects.get(extraction_script_id = pk).pk
        et = ExtractedText.objects.filter(extraction_script = pk).first()
        self.assertTrue( et.qa_group_id == group_pk )
        # The link on the QA index page should now say "Continue QA"
        response = self.client.get(f'/qa/')
        self.assertIn(f"'/qa/extractionscript/15/\'> Continue QA".encode() , response.content)


    def test_qa_script_without_ext_text(self):
        # Begin from the QA index page
        response = self.client.get(f'/qa/')
        self.assertIn(f"/qa/extractionscript/15/'> Begin QA".encode() , response.content)
        # Script 9 has no ExtractedText objects
        pk = 9
        # a user will see no link on the QA index page, but it's still
        # possible to enter the URL
        response = self.client.get(f'/qa/extractionscript/{pk}/', follow=True)
        self.assertEqual(response.status_code, 200)


    def test_data_document_qa(self):
        # Open the QA page for an ExtractedText record that has no QA group
        # and is in a Script with < 100 documents
        pk = ExtractedText.objects.filter( qa_group=None  ).first().pk
        response = self.client.get(f'/datadocument/qa/extractedtext/{pk}/')
        
        # After opening the QA link from the data document detail page, the 
        # following should be true:
        # One new QA group should be created
        scr = ExtractedText.objects.get(pk=pk).extraction_script

        group_count = QAGroup.objects.filter(extraction_script = scr).count()
        self.assertTrue( group_count == 1)
        # The ExtractionScript's qa_begun property should be set to True
        self.assertTrue( scr.qa_begun )
        # The ExtractedText object should be assigned to the QA Group
        new_group = QAGroup.objects.get(extraction_script = scr)
        et = ExtractedText.objects.get(pk=pk)
        self.assertTrue( et.qa_group == new_group )
        # The link on the QA index page should now say "Continue QA"
        response = self.client.get(f'/qa/')
        self.assertIn(f"'/qa/extractionscript/{scr.pk}/\'> Continue QA".encode() , response.content)

        # Open the QA page for an ExtractedText record that has no QA group and
        # is related to a script with over 100 documents
        pk = ExtractedText.objects.filter( extraction_script_id = 12  ).first().pk
        response = self.client.get(f'/datadocument/qa/extractedtext/{pk}/')
        scr = ExtractedText.objects.get(pk=pk).extraction_script
        # After opening the QA link from the data document detail page, the 
        # following should be true:
        # One new QA group should be created
        new_group = QAGroup.objects.get(extraction_script = scr)
        
        # There should be a lot of ExtractedText records assigned to the QA Group
        initial_qa_count = ExtractedText.objects.filter(qa_group = new_group ).count()
        self.assertTrue( initial_qa_count > 100 )
        
        # Select adocument that shares a Script with the
        # QA Group created above BUT DOES NOT BELONG TO THE QA GROUP
        pk = ExtractedText.objects.filter( extraction_script_id = 12).filter(qa_group = None ).first().pk
        # Open its QA page via the /datdocument/qa path
        response = self.client.get(f'/datadocument/qa/extractedtext/{pk}/')
        # Make sure that the number of documents in the QA Group has increased
        self.assertTrue(ExtractedText.objects.filter(qa_group = new_group ).count() > initial_qa_count )



        
       







    def test_dd_link(self):
        # Open the Script page to create a QA Group
        response = self.client.get('/qa/extractedtext/5', follow=True)
        self.assertIn(b'/datadocument/5', response.content)

    def test_approval(self):
        # Open the Script page to create a QA Group
        response = self.client.get('/qa/extractionscript/5', follow=True)
        # Follow the first approval link
        response = self.client.get('/qa/extractedtext/7', follow=True)
        # print(response.context['extracted_text'])

    def test_chemical_presence_formset(self):
        # Open the Script page to create a QA Group
        response = self.client.get('/qa/extractionscript/11', follow=True)
        # Follow the first approval link
        response = self.client.get('/qa/extractedtext/254781', follow=True)
        self.assertIn(b'<input type="text" name="presence-0-raw_cas" value="0000064-17-5"', response.content)
        self.assertIn(b'<input type="text" name="presence-0-raw_chem_name" value="sd alcohol 40-b (ethanol)"', response.content)
        # Check for the presence of the new Chemical Presence-specific class tags
        self.assertIn(b'class="detail-control form-control CP"', response.content)

    def test_hidden_fields(self):
        '''ExtractionScript 15 includes a functional use data group with pk = 5.
        Its QA page should hide the composition fields '''
        # Create the QA group by opening the Script's page
        response = self.client.get('/qa/extractionscript/15/', follow=True)
        # Open the DataGroup's first QA approval link
        response = self.client.get('/qa/extractedtext/5/', follow=True)
        # A raw_cas field should be in the page
        self.assertIn(b'<input type="text" name="uses-1-raw_cas"', response.content)
        # There should not be any unit_type field in the functional use QA display
        self.assertNotIn(b'<input type="text" name="uses-1-unit_type"', response.content)
        # The values shown should match the functional use record, not the chemical record
        self.assertIn(b'Functional Use Chem1', response.content)

        # Go back to a different ExtractionScript
        response = self.client.get('/qa/extractionscript/5', follow=True)
        # Open the QA page for a non-FunctionalUse document
        response = self.client.get('/qa/extractedtext/7/', follow=True)
        # This page should include a unit_type input form
        self.assertIn(b'chemicals-1-unit_type', response.content)
