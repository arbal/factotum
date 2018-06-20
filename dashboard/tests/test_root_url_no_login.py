from django.urls import resolve
from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import AnonymousUser, User
from dashboard.views import index
from dashboard.models import DataDocument, DataGroup, DataSource


class DashboardIndexTest(TestCase):

    def setUp(self):
        self.c = Client()
        self.user = User.objects.create_user(
            username='jdoe', email='jon.doe@epa.gov', password='Sup3r_secret')
        ds = DataSource.objects.create(title="my DS")
        dg = DataGroup.objects.create(name="Test", downloaded_at="2018-01-09 10:12:09", data_source=ds,
                                      zip_file="some.zip", downloaded_by=self.user)
        dd = DataDocument.objects.create(filename="some.pdf", title="My Document", data_group=dg)

    def test_root_url_resolves_to_index_view(self):
        found = resolve('/')
        self.assertEqual(found.func, index)

    def test_dashboard_login_not_required(self):
        response = self.c.get('/')
        self.assertEqual(response.status_code, 200, "Should not redirect to login.")
