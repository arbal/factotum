from django.test import TestCase

from dashboard.forms import DataGroupForm
from dashboard.forms.data_group import RegisterRecordsFormSet
from dashboard.tests.factories import DataSourceFactory, DataGroupFactory
from dashboard.tests.loader import fixtures_standard


class DataGroupTest(TestCase):
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

    def test_datasource_change(self):
        """Verify that a data group's data source can be changed without breaking functionality."""
        self.client.login(username="Karyn", password="specialP@55word")

        datasource_original = DataSourceFactory()
        datasource_new = DataSourceFactory()
        datagroup = DataGroupFactory(data_source=datasource_original)

        self.assertEqual(datasource_original.datagroup_set.count(), 1)
        self.assertEqual(datasource_new.datagroup_set.count(), 0)
        self.assertEqual(datagroup.data_source, datasource_original)

        form_data = {
            "name": datagroup.name,
            "description": datagroup.description,
            "url": datagroup.url,
            "downloaded_by": datagroup.downloaded_by.pk,
            "downloaded_at": datagroup.downloaded_at,
            "download_script": datagroup.download_script.pk
            if datagroup.download_script
            else None,
            "data_source": datasource_new.pk,
        }
        dg_form = DataGroupForm(form_data, instance=datagroup)
        dg_form.fields.pop("group_type")

        self.assertTrue(dg_form.is_valid())
        dg_form.save()

        self.assertEqual(datasource_original.datagroup_set.count(), 0)
        self.assertEqual(datasource_new.datagroup_set.count(), 1)
        self.assertEqual(datagroup.data_source, datasource_new)


class DataGroupCodes(TestCase):

    fixtures = fixtures_standard

    def setUp(self):
        self.client.login(username="Karyn", password="specialP@55word")

    def test_code_table_present(self):
        response = self.client.get("/datasource/18/datagroup_new/")
        self.assertIn("<td>MS</td>", response.content.decode("utf-8"))
