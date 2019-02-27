from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User
from dashboard.tests.loader import load_model_objects
from dashboard.models import ExtractedCPCat, DataDocument


# model test
class CPCatTest(TestCase):

    def setUp(self):
        self.objects = load_model_objects()

    def test_cpcat_creation(self):
        cpdoc = DataDocument.objects.create(title='test CPCat document',
                            data_group=self.objects.dg,
                            document_type=self.objects.dt,
                            filename='example.pdf')

        cpc = ExtractedCPCat.objects.create(
                            prod_name='test prod',
                            cat_code='catcode',
                            description_cpcat='Test Extracted CPCat Record',
                            cpcat_code='excpcat',
                            cpcat_sourcetype='sourcetype',
                            data_document=cpdoc,
                            extraction_script=self.objects.exscript
                            )
        self.assertEqual(cpc.__str__(), cpc.prod_name)
