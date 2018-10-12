from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from dashboard.tests.loader import load_model_objects
from dashboard.models import ExtractedText, QANotes


class ExtractedTest(TestCase):

    def setUp(self):
        self.objects = load_model_objects()

    def test_extracted_doc_date_validation(self):
        # check validation for proper length string
        text = ExtractedText(doc_date= 'Wednesday, January 21, 2014',
                                data_document=self.objects.doc,
                                extraction_script=self.objects.script)
        self.assertRaises(ValidationError, text.clean())
        # check validation not thrown for arbitrary date string less than 25 chars
        text = ExtractedText(doc_date= 'January 1984',
                             data_document=self.objects.doc,
                             extraction_script=self.objects.script)
        try:
            text.clean()
        except ValidationError:
            self.fail("clean() raised ExceptionType unexpectedly!")

        # check validation not thrown if doc_date is null
        text = ExtractedText(data_document=self.objects.doc,
                                extraction_script=self.objects.script)
        try:
            text.clean()
        except ValidationError:
            self.fail("clean() raised ExceptionType unexpectedly!")

    def test_extracted_text_qa_notes(self):
        self.objects.extext.qa_edited = True
        note = QANotes.objects.create(extracted_text=self.objects.extext)
        self.assertEqual(note.qa_notes, None)
        self.assertRaises(ValidationError, note.clean)
