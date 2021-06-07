from django.test import TestCase, tag
from django.urls import resolve
from django.db.utils import IntegrityError

from dashboard import views
from dashboard.forms import create_detail_formset
from dashboard.tests.loader import load_model_objects

from dashboard.models import ExtractedHabitsAndPracticesToPUC, GroupType


@tag("loader")
class HabitViewTest(TestCase):
    multi_db = True

    def setUp(self):
        self.objects = load_model_objects()

    def test_habitsandpractices(self):
        found = resolve(f"/habitsandpractices/{self.objects.doc.pk}/")
        self.assertEqual(found.func, views.habitsandpractices)

    @tag("puc")
    def test_link_habitandpractice_to_puc(self):
        found = resolve(f"/link_habitandpractice_to_puc/{self.objects.ehp.pk}/")
        self.assertEqual(found.func, views.link_habitsandpractices)

    def test_product_surveyed_field(self):
        self.objects.gt.code = "HP"
        self.objects.gt.save()
        _, HnPFormSet = create_detail_formset(self.objects.doc)
        data = {
            "habits-TOTAL_FORMS": "2",
            "habits-INITIAL_FORMS": "1",
            "habits-MIN_NUM_FORMS": "0",
            "habits-MAX_NUM_FORMS": "1000",
            "habits-0-id": self.objects.ehp.pk,
            "habits-0-data_type": self.objects.ehp_dt.pk,
            "habits-0-product_surveyed": "",
        }
        hp_formset = HnPFormSet(data, prefix="habits")
        self.assertFalse(hp_formset.is_valid())

        data = {
            "habits-TOTAL_FORMS": "2",
            "habits-INITIAL_FORMS": "1",
            "habits-MIN_NUM_FORMS": "0",
            "habits-MAX_NUM_FORMS": "1000",
            "habits-0-id": self.objects.ehp.pk,
            "habits-0-data_type": self.objects.ehp_dt.pk,
            "habits-0-product_surveyed": "monster trucks",
        }
        hp_formset = HnPFormSet(data, prefix="habits")

        self.assertTrue(hp_formset.is_valid())

    def test_data_type_field(self):
        self.objects.gt.code = "HP"
        self.objects.gt.save()
        _, HnPFormSet = create_detail_formset(self.objects.doc)
        data = {
            "habits-TOTAL_FORMS": "2",
            "habits-INITIAL_FORMS": "1",
            "habits-MIN_NUM_FORMS": "0",
            "habits-MAX_NUM_FORMS": "1000",
            "habits-0-id": self.objects.ehp.pk,
            "habits-0-data_type": None,
            "habits-0-product_surveyed": "monster trucks",
        }
        hp_formset = HnPFormSet(data, prefix="habits")
        self.assertFalse(hp_formset.is_valid())

        data = {
            "habits-TOTAL_FORMS": "2",
            "habits-INITIAL_FORMS": "1",
            "habits-MIN_NUM_FORMS": "0",
            "habits-MAX_NUM_FORMS": "1000",
            "habits-0-id": self.objects.ehp.pk,
            "habits-0-data_type": self.objects.ehp_dt.pk,
            "habits-0-product_surveyed": "monster trucks",
        }
        hp_formset = HnPFormSet(data, prefix="habits")

        self.assertTrue(hp_formset.is_valid())

    def test_edit_hnp_detail(self):
        """This page may not be in use anymore."""
        self.objects.exscript.title = "Manual (dummy)"
        self.objects.exscript.save()
        self.objects.ehp.data_document.data_group.group_type = GroupType.objects.create(
            code="HP"
        )
        self.objects.ehp.data_document.data_group.save()
        self.client.login(username="Karyn", password="specialP@55word")
        pk = self.objects.ehp.data_document.pk
        response = self.client.get(f"/habitsandpractices/{pk}/")
        self.assertNotContains(response, "Raw Category", html=True)

        # Ensure there are Cancel and Back buttons with the correct URL to return to the DG detail page
        self.assertContains(
            response,
            f'href="/datagroup/{self.objects.ehp.data_document.data_group.pk}/" role="button">Cancel</a>',
        )
        self.assertContains(
            response,
            f'href="/datagroup/{self.objects.ehp.data_document.data_group.pk}/" role="button">Back</a>',
        )

        # Ensure that the URL above responds correctly
        response2 = self.client.get(f"/datagroup/{self.objects.dg.pk}/")
        self.assertContains(response2, "Data Group Detail: Data Group for Test")

    @tag("puc")
    def test_unique_constaint(self):
        self.ehp1 = ExtractedHabitsAndPracticesToPUC.objects.create(
            extracted_habits_and_practices=self.objects.ehp, PUC=self.objects.puc
        )

        with self.assertRaises(IntegrityError):
            self.ehp2 = ExtractedHabitsAndPracticesToPUC.objects.create(
                extracted_habits_and_practices=self.objects.ehp, PUC=self.objects.puc
            )
