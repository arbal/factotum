from django.test import TestCase, TransactionTestCase

from dashboard.forms.data_group import RegisterRecordsFormSet
from dashboard.tests.factories import DataSourceFactory
from dashboard.tests.loader import fixtures_standard


class DataGroupTest(TransactionTestCase):
    fixtures = ["00_superuser"]

    def test_redirect_if_not_logged_in(self):
        response = self.client.get("/datagroups/")
        self.assertEqual(
            response.status_code, 302, "User should be redirected to login"
        )
        self.assertEqual(
            response.url,
            "/login/?next=/datagroups/",
            "User should be sent to login page",
        )

    def test_headers_on_create_page(self):
        """Verify the headers from RegisterRecordsFormSet are somewhere visible on the page.
        These headers are used in the CSV upload
        """
        self.client.login(username="Karyn", password="specialP@55word")
        ds = DataSourceFactory()

        response = self.client.get(f"/datasource/{ds.pk}/datagroup_new/")
        self.assertIn(
            ", ".join(RegisterRecordsFormSet.header_cols),
            response.content.decode("utf-8"),
        )


class DataGroupCodes(TestCase):

    fixtures = fixtures_standard

    def setUp(self):
        self.client.login(username="Karyn", password="specialP@55word")

    def test_code_table_present(self):
        response = self.client.get("/datasource/18/datagroup_new/")
        self.assertIn("<td>MS</td>", response.content.decode("utf-8"))
