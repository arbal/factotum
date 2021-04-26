from django.test import TestCase, override_settings
from django.test.client import Client
from django.urls import reverse

from dashboard.models import FunctionalUse, FunctionalUseCategory
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
        categorized_fu = surfactants.filter(category__isnull=False).first()

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
