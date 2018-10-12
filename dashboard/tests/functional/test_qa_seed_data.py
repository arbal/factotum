from django.test import Client
from django.test import TestCase, override_settings, RequestFactory
from dashboard.models import DataDocument, Script, ExtractedText, ExtractedChemical, QAGroup

@override_settings(ALLOWED_HOSTS=['testserver'])
class TestQaPage(TestCase):
    fixtures = ['00_superuser.yaml','01_lookups.yaml',
    '02_datasource.yaml','03_datagroup.yaml',
    '04_PUC.yaml','05_product.yaml',
    '06_datadocument.yaml','07_script.yaml',
    '08_extractedtext.yaml','09_productdocument.yaml',
    '10_extractedchemical.yaml', '11_dsstoxsubstance.yaml',
    '15_extractedfunctionaluse.yaml']

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

    def test_approval(self):
        # Open the Script page to create a QA Group
        response = self.client.get('/qa/extractionscript/5', follow=True)
        # Follow the first approval link
        response = self.client.get('/qa/extractedtext/7', follow=True)
        # print(response.context['extracted_text'])


    def test_hidden_fields(self):
        '''ExtractionScript 15 includes a functional use data group with pk = 5.
        Its QA page should hide the composition fields '''
        # Create the QA group by opening the Script's page
        response = self.client.get('/qa/extractionscript/15', follow=True)
        # Open the DataGroup's first QA approval link
        response = self.client.get('/qa/extractedtext/5/', follow=True)
        # A raw_cas field should be in the page
        self.assertIn(b'<input type="text" name="details-1-raw_cas"', response.content)
        # There should not be any unit_type field in the functional use QA display
        self.assertNotIn(b'<input type="text" name="details-1-unit_type"', response.content)
        # The values shown should match the functional use record, not the chemical record
        self.assertIn(b'Functional Use Chem1', response.content)

        # Go back to a different ExtractionScript
        response = self.client.get('/qa/extractionscript/5', follow=True)
        # Open the QA page for a non-FunctionalUse document
        response = self.client.get('/qa/extractedtext/7/', follow=True)
        # This page should include a unit_type input form
        self.assertIn(b'details-1-unit_type', response.content)
