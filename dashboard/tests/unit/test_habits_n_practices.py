from django.urls import resolve
from django.test import TestCase
from django.http import HttpRequest
from dashboard.tests.loader import load_model_objects
from dashboard import views
from dashboard.models import *



class HabitViewTest(TestCase):

    def setUp(self):
        self.objects = load_model_objects()
        self.hnp = ExtractedHabitsAndPractices.objects.create(
                                            extracted_text=self.objects.extext)

    def test_habitsandpractices(self):
        found = resolve(f'/habitsandpractices/{self.objects.doc.pk}')
        self.assertEqual(found.func, views.habitsandpractices)

    def test_link_habitandpractice_to_puc(self):
        found = resolve(f'/link_habitandpractice_to_puc/{self.hnp.pk}')
        self.assertEqual(found.func, views.link_habitsandpractices)
