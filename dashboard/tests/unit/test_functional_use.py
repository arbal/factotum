from django.core.exceptions import ValidationError
from django.test import TestCase
from dashboard.tests.factories import (
    FunctionalUseFactory,
    ExtractedCompositionFactory,
    FunctionalUseCategoryFactory,
)


class FunctionalUseTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.base_category = FunctionalUseCategoryFactory()
        cls.alt_category = FunctionalUseCategoryFactory()

    def test_report_funcuse_unique_to_category(self):
        """Reported functional use strings may only be linked to one FunctionalUseCategory

        Given this functional use
        base_functional_use = FunctionalUse(
            report_funcuse='a',
            category=1
        )

        then functional uses associated with the same report_funcuse but no category would be valid
        valid_functional_use = FunctionalUse(
            report_funcuse='a',
            category=None
        )

        but a functional use associated to a new category would be invalid
        invalid_functional_use = FunctionalUse(
            report_funcuse='a',
            category=2
        )
        """

        base_functional_use = FunctionalUseFactory(
            report_funcuse="report_funcuse",
            category=self.base_category,
            chem=ExtractedCompositionFactory(),
        )

        valid_functional_use = FunctionalUseFactory.build(
            report_funcuse="report_funcuse",
            category=None,
            chem=ExtractedCompositionFactory(),
        )
        self.assertIsNone(valid_functional_use.full_clean())

        invalid_functional_use = FunctionalUseFactory.build(
            report_funcuse="report_funcuse",
            category=self.alt_category,
            chem=ExtractedCompositionFactory(),
        )
        self.assertRaises(ValidationError, invalid_functional_use.full_clean)

        # Assert reported functional use can be edited
        base_functional_use.report_funcuse = "edited"
        self.assertIsNone(base_functional_use.full_clean())
        base_functional_use.save()  # saving to prevent having to revert report_funcuse field.

        # Assert category can be changed
        base_functional_use.category = self.alt_category
        self.assertIsNone(base_functional_use.full_clean())
        base_functional_use.save()
