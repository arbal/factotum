from django.urls import resolve, reverse
from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import AnonymousUser, User
from dashboard.views import index
from dashboard.models import (
    DataDocument,
    DataGroup,
    DataSource,
    GroupType,
    ExtractedListPresenceTag,
    ExtractedListPresenceTagKind,
    News,
)


class RootUrlNoLoginTest(TestCase):
    def setUp(self):
        self.c = Client()
        self.user = User.objects.create_user(
            username="jdoe", email="jon.doe@epa.gov", password="Sup3r_secret"
        )
        ds = DataSource.objects.create(title="my DS")
        gt = GroupType.objects.create(
            title="Unidentified", description="Unidentified Group Type"
        )
        dg = DataGroup.objects.create(
            name="Test",
            downloaded_at="2018-01-09 10:12:09",
            data_source=ds,
            downloaded_by=self.user,
            group_type=gt,
        )
        dd = DataDocument.objects.create(
            filename="some.pdf", title="My Document", data_group=dg
        )
        lptk = ExtractedListPresenceTagKind.objects.create(name="Example kind")
        lpt = ExtractedListPresenceTag.objects.create(
            kind=lptk, name="example", slug="example", id=1
        )
        gs = News.objects.create(
            subject="Getting Started",
            section=News.GETTING_STARTED_SECTION_NAME,
            body="Getting started with Factotum is fun and easy...",
        )
        for i in ["First", "Second", "Third", "Fourth", "Fifth", "Sixth"]:
            News.objects.create(
                subject=f"{i} News Article", body=f"{i} in a series of news articles"
            )

    def test_root_url_resolves_to_index_view(self):
        found = resolve("/")
        self.assertEqual(found.func, index)

    def test_dashboard_news(self):
        response = self.c.get("/")
        self.assertEqual(response.status_code, 200, "Should display the front page.")

        html = response.content.decode("utf-8")

        self.assertInHTML("Getting Started", html)
        self.assertInHTML("<div>Sixth in a series of news articles</div>", html)
        # the first article should have been pushed off the home page
        with self.assertRaises(AssertionError):
            self.assertInHTML("<div>First in a series of news articles</div>", html)

    def test_dashboard_login_not_required(self):
        response = self.c.get("/")
        self.assertEqual(response.status_code, 200, "Should not redirect to login.")

    def test_puc_list_login_not_required(self):
        response = self.c.get("/pucs/")
        self.assertEqual(response.status_code, 200, "Should not redirect to login.")

    def test_list_presence_tag_list_login_not_required(self):
        response = self.c.get("/list_presence_tags/")
        self.assertEqual(response.status_code, 200, "Should not redirect to login.")

    def test_list_presence_tag_detail_login_not_required(self):
        path = reverse("lp_tag_detail", args=[1])
        response = self.c.get(path)
        self.assertEqual(response.status_code, 200, "Should not redirect to login.")
