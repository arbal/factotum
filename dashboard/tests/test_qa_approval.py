from django.test import Client
from django.test import TestCase, override_settings, RequestFactory
from dashboard.models import DataDocument, Script, ExtractedText, ExtractedChemical, QAGroup

@override_settings(ALLOWED_HOSTS=['testserver'])
class TestApprovalView(TestCase):
    fixtures = ['00_superuser.yaml','01_lookups.yaml',
    '02_datasource.yaml','03_datagroup.yaml',
    '04_productcategory.yaml','05_product_lite.yaml',
    '06_datadocument_lite.yaml','07_script.yaml',
    '08_extractedtext_lite.yaml','09_productdocument_lite.yaml',
    '10_extractedchemical.yaml']
    def setUp(self):
        print('setUp running')
        self.factory = RequestFactory()
        self.client.login(username='karyn', password='specialP@55word')


    def test_qa_begin(self):
        """
        Check that starting the QA process flips the variable on the Script
        """
        self.assertTrue( not Script.objects.get(pk=5).qa_begun, 
        'The Script should have qa_begun of False at the beginning')
        response = self.client.get('/qa/extractionscript/5', follow=True)
        self.assertTrue(Script.objects.get(pk=5).qa_begun, 
        'qa_begun should now be true')
        #self.assertIn(b'<title>factotum</title>', response.content)
        

    def test_approval(self):
        # Open the Script page to create a QA Group
        response = self.client.get('/qa/extractionscript/5', follow=True)
        # Follow the first approval link
        response = self.client.get('/qa/extractedtext/7', follow=True)
        print(response.context['extracted_text'])
        
        




    




