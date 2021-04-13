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
        self.assertEqual(len(combinations), 16, "THere should be 16 combinations")

        surfactants = FunctionalUse.objects.filter(report_funcuse="surfactant")

        # Of the two FunctionalUse records where the report_funcuse is "surfactant",
        # one has a category assigned.
        uncategorized_fu = surfactants.filter(category__isnull=True).first()
        categorized_fu = surfactants.filter(category__isnull=False).first()

        # The first "surfactant" dict in the list is the uncategorized one,
        # the second one is the curated record
        surfactants = []
        for li in combinations:
            if li["report_funcuse"] == "surfactant":
                if li["categorytitle"] == None:
                    self.assertEqual(li["fu_count"], 1)
                if li["categorytitle"] == "solvent":
                    self.assertEqual(li["fu_count"], 1)

        # assign the category and make sure the data payload changed
        cat = categorized_fu.category
        uncategorized_fu = (
            FunctionalUse.objects.filter(report_funcuse="surfactant")
            .filter(category__isnull=True)
            .first()
        )
        uncategorized_fu.category = cat
        uncategorized_fu.save()

        # Now both "surfactant" records should be categorized, so the
        # number of results should be reduced by one
        response = self.client.get(reverse("functional_use_curation"))
        combinations = response.context["combinations"]
        self.assertEqual(
            len(combinations), 15, "There should be 15 combinations after the edit"
        )
