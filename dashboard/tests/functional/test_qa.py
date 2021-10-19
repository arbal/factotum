from lxml import html
from datetime import date

from django.test import TestCase, tag

from dashboard.tests.factories import DataGroupFactory, ExtractedTextFactory

from dashboard.tests.loader import fixtures_standard
from dashboard.models import Script, ExtractedText, RawChem, DataDocument


@tag("loader")
class QATest(TestCase):
    fixtures = fixtures_standard

    def setUp(self):
        self.client.login(username="Karyn", password="specialP@55word")

    def test_qa_scoreboard(self):
        scripts = Script.objects.filter(script_type="EX").exclude(extractedtext=None)
        response = self.client.get("/qa/extractionscript/").content.decode("utf8")
        response_html = html.fromstring(response)

        row_count = len(
            response_html.xpath('//table[@id="extraction_script_table"]/tbody/tr')
        )
        self.assertNotEqual(
            scripts.count(), row_count, ("Scripts w/ CP type texts should be excluded.")
        )

        script = scripts.first()
        href = response_html.xpath(f'//*[@id="script-{script.pk}"]/@href')[0]
        self.assertEqual(
            script.url, href, "There should be an external link to the script."
        )
        td = response_html.xpath(f'//*[@id="docs-{script.pk}"]').pop()
        model_doc_count = ExtractedText.objects.filter(extraction_script=script).count()

        self.assertEqual(
            int(td.text),
            model_doc_count,
            (
                "The displayed number of datadocuments should match "
                "the number whose related extracted text objects used"
                " the extraction script"
            ),
        )

        td = response_html.xpath(f'//*[@id="pct-{script.pk}"]').pop()
        self.assertEqual(
            td.text,
            script.get_pct_checked(),
            ("The displayed percentage should match " "what is derived from the model"),
        )
        self.assertEqual(
            script.get_qa_complete_extractedtext_count(),
            0,
            (
                "The ExtractionScript object should return 0 "
                "qa_checked ExtractedText objects"
            ),
        )

        # Set qa_checked property to True for one of the ExtractedText objects
        et = script.extractedtext_set.first()
        self.assertFalse(et.qa_checked)
        et.qa_checked = True
        et.save()
        self.assertEqual(
            script.get_qa_complete_extractedtext_count(),
            1,
            (
                "The ExtractionScript object should now return "
                "1 qa_checked ExtractedText object"
            ),
        )

        # A button for each row that will take you to the script's QA page
        script_qa_link = response_html.xpath(f'//*[@id="qa-{script.pk}"]/a/@href').pop()
        self.assertIn(f"/qa/extractionscript/{script.pk}/", script_qa_link)

        # Before clicking link, the script's qa_done property should be false
        self.assertFalse(script.qa_begun, "The property should be False")

        # Link should open a page where the h1 text matches title of the Script
        response = self.client.get(script_qa_link)
        response_html = html.fromstring(response.content.decode("utf8"))
        h1 = response_html.xpath(f'//*[@id="script-{script.pk}"]').pop()
        self.assertIn(
            script.title,
            h1.text_content(),
            "The <h1> text should equal the .title of the Script",
        )

        # Opening ExtractionScript QA page should set qa_begun property to True
        script.refresh_from_db()
        self.assertTrue(
            script.qa_begun,
            ("The qa_begun property of the " "ExtractionScript should now be True"),
        )

        # Go back to the QA index page to confirm that the QA is complete
        response = self.client.get("/qa/extractionscript/").content.decode("utf8")
        response_html = html.fromstring(response)
        status = response_html.xpath(f'//*[@id="qa-{script.pk}"]/a').pop()
        self.assertEqual(
            td.text,
            "0 %",
            ("The displayed percentage should match " "what is derived from the model"),
        )
        self.assertIn(
            "QA Complete",
            status.text,
            (
                "The QA Status field should now say "
                '"QA Complete" instead of "Begin QA"'
            ),
        )

    def test_component_label(self):
        data_document = DataDocument.objects.get(pk=354787)
        rawchem = RawChem.objects.get(pk=853)
        component = rawchem.component
        response = self.client.get("/qa/extractedtext/%i/" % data_document.pk)
        response_html = html.fromstring(response.content)
        component_text = response_html.xpath(
            f'//*[@id="component-{rawchem.id}"]/text()'
        )[0]
        self.assertIn(component, component_text)

    def test_qa_compextractionscript(self):
        script = Script.objects.get(pk=12)
        text = ExtractedText.objects.filter(
            qa_group=script.get_or_create_qa_group(), qa_checked=False
        ).first()

        rawchem = RawChem.objects.filter(extracted_text=text).first()
        rawchem.raw_cas = "12345"
        rawchem.save()

        response = self.client.get("/qa/extractionscript/%i/" % script.pk)
        response_html = html.fromstring(response.content)

        date_updated_text = response_html.xpath(
            f'//*[@id="date_updated_{text.pk}"]/text()'
        )[0]
        self.assertIn(date.today().strftime("%b %d, %Y"), date_updated_text)

        # open the first extracted document
        response = self.client.get("/qa/extractedtext/%i/" % text.pk)
        response_html = html.fromstring(response.content)

        # skip button should go to the next extracted text record
        skip_button = response_html.xpath("//*[@id='skip']")[0]
        skip_button_html = html.tostring(skip_button).decode("utf-8")
        next_extracted_text_id = text.next_extracted_text_in_qa_group()
        self.assertIn(
            f'href="/qa/extractedtext/{next_extracted_text_id}/"', skip_button_html
        )

        exit_button = response_html.xpath("//*[@id='exit']")[0]
        exit_button_html = html.tostring(exit_button).decode("utf-8")
        self.assertIn("/qa/extractionscript/12/", exit_button_html)

    def test_qa_pdf_download(self):
        data_document = DataDocument.objects.get(pk=354787)
        response = self.client.get("/qa/extractedtext/%i/" % data_document.pk)
        response_html = html.fromstring(response.content)
        filename = data_document.filename
        self.assertTrue(response_html.xpath(f'//a[@title="{filename}"]'))

    def test_qa_compmanual(self):
        """
        Test the behavior of the manually-extracted Composition QA pages
        """
        MANUAL_SCRIPT_ID = (
            Script.objects.filter(title="Manual (dummy)", script_type="EX").first().id
        )
        script = Script.objects.get(pk=MANUAL_SCRIPT_ID)
        # new extractedtext objects from factories
        dg = DataGroupFactory(name="Manually Extracted Composition Records")
        doc_count = 20
        ets = ExtractedTextFactory.create_batch(
            size=doc_count, extraction_script=script, data_document__data_group=dg
        )

        response = self.client.get("/qa/manualcomposition/")
        response_html = html.fromstring(response.content)

        table_doc_count = response_html.xpath(
            '//*[@id="data_group_table"]/tbody/tr/td[3]'
        )[0].text
        self.assertEqual(str(doc_count), table_doc_count)

        # open the data group's QA page
        response = self.client.get(f"/qa/manualcomposition/{dg.pk}/")
        self.assertEqual(str(response.status_code), "200")

        # open the first extracted document
        response = self.client.get("/qa/extractedtext/%i/" % ets[0].pk)
        response_html = html.fromstring(response.content)
