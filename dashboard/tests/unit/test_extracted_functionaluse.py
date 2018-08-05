from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User
from dashboard.tests.loader import load_model_objects
from dashboard.models import ExtractedFunctionalUse


# model test
class FunctionalUseTest(TestCase):

    def setUp(self):
        self.objects = load_model_objects()

    def test_functionaluse_creation(self):
        fu = ExtractedFunctionalUse(raw_chem_name='test_chem',
                                    extracted_text=self.objects.extext)
        self.assertEqual(fu.__str__(), fu.raw_chem_name)
