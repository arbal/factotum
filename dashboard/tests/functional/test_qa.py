import time
from django.test import TestCase
from dashboard.tests.loader import load_model_objects
from dashboard.models import DataDocument, Script, ExtractedText
from lxml import html

class QATest(TestCase):

    def setUp(self):
        self.objects = load_model_objects()
        self.client.login(username='Karyn', password='specialP@55word')

    def test_qa_scoreboard(self):
        response = self.client.get('/qa/').content.decode('utf8')
        response_html = html.fromstring(response)

        row_count = len(response_html.xpath('//table[@id="extraction_script_table"]/tbody/tr'))
        scriptcount = Script.objects.filter(script_type='EX').count()
        self.assertEqual(scriptcount, row_count, ('The seed data contains 1 '
                                                  'Script object with the script_type'
                                                  'EX, which should appear in this table'))
        displayed_doc_count = response_html.xpath(
            '//*[@id="extraction_script_table"]/tbody/tr[' + str(row_count) + ']/td[2]')[0].text
        model_doc_count = DataDocument.objects.filter(
            extractedtext__extraction_script=self.objects.exscript.pk).count()

        self.assertEqual(displayed_doc_count, str(model_doc_count),
                         ('The displayed number of datadocuments should match '
                          'the number whose related extracted text objects used '
                          ' the extraction script'))

        displayed_pct_checked = response_html.xpath(
            '//*[@id="extraction_script_table"]/tbody/tr[' + str(row_count) + ']/td[3]')[0].text
        model_pct_checked = self.objects.exscript.get_pct_checked()
        self.assertEqual(displayed_pct_checked, model_pct_checked,
                         ('The displayed percentage should match what is derived from the model'))

        es = self.objects.exscript
        self.assertEqual(es.get_qa_complete_extractedtext_count(), 0,
                         ('The ExtractionScript object should return 0 qa_checked ExtractedText objects'))

        # Set qa_checked property to True for one of the ExtractedText objects
        self.assertEqual(self.objects.extext.qa_checked, False)
        self.objects.extext.qa_checked = True
        self.objects.extext.save()
        self.assertEqual(es.get_qa_complete_extractedtext_count(), 1,
                         ('The ExtractionScript object should now return 1 qa_checked ExtractedText object'))

        # A button for each row that will take you to the script's QA page
        script_qa_link = response_html.xpath(
            '//*[@id="extraction_script_table"]/tbody/tr[contains(.,"Test Extraction Script")]/td[4]/a/@href')[0]
        self.assertIn(f'/qa/extractionscript/{str(self.objects.exscript.pk)}/', script_qa_link)

        # Before clicking the link, the script's qa_done property should be false
        self.assertEqual(es.qa_begun, False,
                         'The qa_done property of the Script should be False')

        # The link should open a page where the h1 text matches the title of the Script
        response = self.client.get(script_qa_link).content.decode('utf8')
        response_html = html.fromstring(response)
        self.assertIn(es.title, response_html.xpath('/html/body/div/h1/text()')[0],
                      'The <h1> text should equal the .title of the Script')

        # Opening the ExtractionScript's QA page should set its qa_begun property to True
        es.refresh_from_db()
        self.assertEqual(es.qa_begun, True,
                         'The qa_begun property of the ExtractionScript should now be True')

        # Go back to the QA index page to confirm
        response = self.client.get('/qa/').content.decode('utf8')
        response_html = html.fromstring(response)
        script_qa_link = response_html.xpath(
            '//*[@id="extraction_script_table"]/tbody/tr[contains(.,"Test Extraction Script")]/td[4]/a/text()')[0]
        self.assertIn('Continue QA', script_qa_link,
                      'The QA button should now say "Continue QA" instead of "Begin QA"')
