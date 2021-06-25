from django.test import TestCase, override_settings
from django.test.client import Client
from django.urls import reverse

from dashboard.models import (
    FunctionalUse,
    FunctionalUseCategory,
    FunctionalUseToRawChem,
)
from dashboard.tests.loader import fixtures_standard


@override_settings(ALLOWED_HOSTS=["testserver"])
class TestFunctionalUseCuration(TestCase):
    fixtures = fixtures_standard

    def setUp(self):
        self.client = Client()
        self.client.login(username="Karyn", password="specialP@55word")

    def test_functional_use_list(self):
        response = self.client.get(reverse("functional_use_curation"))
        combinations = response.context["combinations"]
        # One row for each functional use
        self.assertEqual(
            len(combinations),
            FunctionalUse.objects.count(),
            f"There should be {FunctionalUse.objects.count()} combinations",
        )

        surfactants = FunctionalUse.objects.filter(report_funcuse="surfactant")

        # Of the two FunctionalUse records where the report_funcuse is "surfactant",
        # one has a category assigned.
        self.assertFalse(
            surfactants.filter(category__isnull=True).exists(),
            "All functional uses are supposed to be harmonized if one is harmonized.",
        )

        # The first "surfactant" dict in the list is the uncategorized one,
        # the second one is the curated record
        surfactants = []
        for li in combinations:
            if li["report_funcuse"] == "surfactant":
                if li["categorytitle"] == "solvent":
                    self.assertEqual(li["fu_count"], 2)

        # Now both "surfactant" records should be categorized, so the
        # number of results should be reduced by one
        response = self.client.get(reverse("functional_use_curation"))
        combinations = response.context["combinations"]
        self.assertEqual(
            len(combinations), 16, "There should be 16 combinations after the edit"
        )

    def test_functional_use_cleanup(self):
        # cut linkage and invoke cleanup
        FunctionalUseToRawChem.objects.all().delete()
        self.client.post(reverse("functional_use_cleanup"))

        response = self.client.get(reverse("functional_use_curation"))
        combinations = response.context["combinations"]
        self.assertEqual(len(combinations), 0, f"There should be 0 combinations")

    def test_functional_use_unassignment(self):
        """
        Confirm that the unassign_functional_uses
        view destroys the FunctionalUseToRawChem 
        records 
        """
        self.assertEqual(
            FunctionalUseToRawChem.objects.filter(functional_use_id=6).count(),
            2,
            f"There should be 2 assignments",
        )
        self.client.post(reverse("unassign_functional_uses", args=[6]))
        self.assertEqual(
            FunctionalUseToRawChem.objects.filter(functional_use_id=6).count(),
            0,
            f"There should be 0 assignments",
        )
