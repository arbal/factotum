from django.test import TestCase
from .loader import load_model_objects
from dashboard.models import DataGroup
from dashboard.views.data_group import ExtractionScriptForm, DataGroupForm
from django.core.files.uploadedfile import SimpleUploadedFile

from django.test import Client
from importlib import import_module


class DataGroupTest(TestCase):

    def setUp(self):
        self.objects = load_model_objects()
        self.client.login(username='Karyn', password='specialP@55word')

    def test_detail_form_load(self):
        pk = self.objects.dg.pk
        response = self.client.get(f'/datagroup/{pk}')
        self.assertFalse(self.objects.doc.matched,
                    ('Document should start w/ matched False'))
        self.assertFalse(self.objects.doc.extracted,
                    ('Document should start w/ extracted False'))
        self.assertTrue(response.context['upload_form'],
                    ('UploadForm should be included in the page!'))
        self.assertFalse(response.context['extract_form'],
                    ('ExtractForm should not be included in the page!'))
        self.objects.doc.matched = True
        self.objects.doc.save()
        response = self.client.get(f'/datagroup/{pk}')
        self.assertFalse(response.context['upload_form'], (
                    'UploadForm should not be included in the page!'))
        self.assertIsInstance(response.context['extract_form'],
                                            ExtractionScriptForm,
                    ('ExtractForm should be included in the page!'))
        self.objects.doc.extracted = True
        self.objects.doc.save()
        response = self.client.get(f'/datagroup/{pk}')
        self.assertFalse(response.context['upload_form'],
                    ('UploadForm should not be included in the page!'))
        self.assertFalse(response.context['extract_form'],
                    ('ExtractForm should not be included in the page!'))

    def test_detail_template_fieldnames(self):
        pk = self.objects.dg.pk
        self.assertEqual(str(self.objects.dg.group_type),'Composition',
        'Type of DataGroup needs to be "composition" for this test.')
        response = self.client.get(f'/datagroup/{pk}')
        self.assertEqual(response.context['extract_fields'],
                ['data_document_id','data_document_filename', 'record_type',
                'prod_name','doc_date','rev_num', 'raw_cas', 'raw_chem_name',
                'report_funcuse','raw_min_comp','raw_max_comp', 'unit_type',
                'ingredient_rank', 'raw_central_comp'],
                "Fieldnames passed are incorrect!")
        self.objects.gt.title = 'Functional_use'
        self.objects.gt.save()
        self.assertEqual(str(self.objects.dg.group_type),'Functional_use',
            'Type of DataGroup needs to be "Functional_use" for this test.')
        response = self.client.get(f'/datagroup/{pk}')
        self.assertEqual(response.context['extract_fields'],
                ['data_document_id','data_document_filename', 'record_type',
                'prod_name','doc_date','rev_num', 'raw_cas', 'raw_chem_name',
                'report_funcuse'],
                "Fieldnames passed are incorrect!")

    def test_unidentifed_group_type(self):
        pk = self.objects.dg.pk
        self.objects.doc.matched = True
        self.objects.doc.save()
        response = self.client.get(f'/datagroup/{pk}')
        self.assertIsInstance(response.context['extract_form'],
                                            ExtractionScriptForm,
                    ('ExtractForm should be included in the page!'))
        self.objects.gt.title = 'Unidentified'
        self.objects.gt.save()
        response = self.client.get(f'/datagroup/{pk}')
        self.assertFalse(response.context['extract_form'],
                    ('ExtractForm should not be included in the page!'))
# <!-- request.POST -->
# <QueryDict: {'csrfmiddlewaretoken': ['hhkUa1TcXA8sOtgcUjPEQRe5MnEIILEh4EVp5P4E3P3YIJiAsPWKaw6qKd41SldU'],
# 'script_selection': ['5'],
# 'weight_fraction_type': ['1'],
# 'extract_button': ['Submit']}>
#
# <!-- request.FILES -->
# <MultiValueDict: {'extract_file': [<InMemoryUploadedFile: extracted_text_invalid_choices.csv (text/csv)>]}>
