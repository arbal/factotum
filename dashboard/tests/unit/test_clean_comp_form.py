from decimal import Decimal

from django.test import TestCase

from dashboard.forms.data_group import CleanCompForm
from dashboard.tests import factories


class CleanCompFormTest(TestCase):
    """This is the base form used to make up CleanCompFormSet.
    Due to this it does not have a "save" function."""

    def setUp(self):
        self.extracted_chem = factories.ExtractedCompositionFactory()
        self.weight_fraction_type = factories.WeightFractionTypeFactory()

        self.base_form_data = {
            "cleaning_script_id": self.extracted_chem.extracted_text.cleaning_script_id,
            "ExtractedComposition_id": self.extracted_chem.pk,
            "weight_fraction_type_id": self.weight_fraction_type.pk,
            "lower_wf_analysis": "0.0",
            "central_wf_analysis": "",
            "upper_wf_analysis": "1.0",
        }

    def _update_base_form_data(self, **kwargs):
        form_data = self.base_form_data.copy()
        form_data.update(**kwargs)
        return form_data

    def test_valid_outer_wf(self):
        form = CleanCompForm(self.base_form_data)
        self.assertTrue(form.is_valid())

    def test_valid_central_wf(self):
        form = CleanCompForm(
            {
                "cleaning_script_id": self.extracted_chem.extracted_text.cleaning_script_id,
                "ExtractedComposition_id": self.extracted_chem.pk,
                "weight_fraction_type_id": self.weight_fraction_type.pk,
                "lower_wf_analysis": "",
                "central_wf_analysis": "0.5",
                "upper_wf_analysis": "",
            }
        )
        self.assertTrue(form.is_valid())

    def test_invalid_chemical(self):
        form = CleanCompForm(self._update_base_form_data(ExtractedComposition_id=None))
        self.assertFalse(form.is_valid())
        self.assertIsNotNone(form.errors.get("ExtractedComposition_id"))

    def test_invalid_wf_required(self):
        form_missing_wf = CleanCompForm(
            self._update_base_form_data(lower_wf_analysis="", upper_wf_analysis="")
        )

        self.assertFalse(form_missing_wf.is_valid())
        # this is a non-field error
        self.assertIsNotNone(form_missing_wf.errors.get("__all__"))

    def test_invalid_upper_and_lower_wf_required_together(self):
        form_missing_lower = CleanCompForm(
            self._update_base_form_data(lower_wf_analysis="")
        )
        form_missing_upper = CleanCompForm(
            self._update_base_form_data(upper_wf_analysis="")
        )

        self.assertFalse(form_missing_lower.is_valid())
        self.assertIsNotNone(form_missing_lower.errors.get("lower_wf_analysis"))

        self.assertFalse(form_missing_upper.is_valid())
        self.assertIsNotNone(form_missing_upper.errors.get("upper_wf_analysis"))

    def test_invalid_wf_boundary(self):
        form_negative = CleanCompForm(
            self._update_base_form_data(lower_wf_analysis="-1")
        )
        form_gt_one = CleanCompForm(self._update_base_form_data(upper_wf_analysis="2"))
        form_invalid_data = CleanCompForm(
            self._update_base_form_data(upper_wf_analysis="a")
        )

        self.assertFalse(form_negative.is_valid())
        self.assertIsNotNone(form_negative.errors.get("lower_wf_analysis"))

        self.assertFalse(form_gt_one.is_valid())
        self.assertIsNotNone(form_gt_one.errors.get("upper_wf_analysis"))

        self.assertFalse(form_invalid_data.is_valid())
        self.assertIsNotNone(form_invalid_data.errors.get("upper_wf_analysis"))
