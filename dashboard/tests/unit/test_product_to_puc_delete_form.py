from django.test import TestCase

from dashboard.forms.forms import BulkProductToPUCDeleteForm
from dashboard.models import ProductToPUC
from dashboard.tests.factories import ProductToPUCFactory, UserFactory


class TestBulkProductToPUCDeleteForm(TestCase):
    fixtures = ["00_superuser"]
    form = BulkProductToPUCDeleteForm

    @classmethod
    def setUpTestData(cls):
        cls.p2p = ProductToPUCFactory()

    def test_successful_form(self):
        """Test form can be validated and saved with valid data"""

        # Make a second factory to test bulk
        p2p_2 = ProductToPUCFactory()

        pk_str = f"{self.p2p.pk},{p2p_2.pk}"
        form = self.form({"p2p_ids": pk_str})

        self.assertTrue(form.is_valid())
        saved_response = form.save()

        self.assertEqual(saved_response, form.SUCCESS_MESSAGE % 2)

    def test_successful_form_duplicate_request(self):
        """Resubmissions pass silently with no additional deletions"""
        pk = self.p2p.pk
        form = self.form({"p2p_ids": pk})
        form2 = self.form({"p2p_ids": pk})

        self.assertTrue(form.is_valid())
        saved_response = form.save()

        self.assertEqual(ProductToPUC.objects.filter(pk=pk).exists(), 0)

        self.assertTrue(form2.is_valid())
        saved_response2 = form2.save()

        self.assertEqual(ProductToPUC.objects.filter(pk=pk).exists(), 0)
        self.assertEqual(saved_response, saved_response2)

    def test_failure_blank_form(self):
        form = self.form({"p2p_ids": ""})
        self.assertFalse(form.is_valid())
        self.assertIn(form.DELETION_REQUIRED_ERROR_MESSAGE, form.non_field_errors())
