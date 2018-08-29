from django.urls import resolve
from django.test import TestCase
from django.http import HttpRequest

from dashboard.tests.loader import load_model_objects
from dashboard import views
from dashboard.models import *
from dashboard.forms import HnPFormSet



class HabitViewTest(TestCase):
    multi_db = True
    def setUp(self):
        self.objects = load_model_objects()


    def test_habitsandpractices(self):
        found = resolve(f'/habitsandpractices/{self.objects.doc.pk}/')
        self.assertEqual(found.func, views.habitsandpractices)

    def test_link_habitandpractice_to_puc(self):
        found = resolve(f'/link_habitandpractice_to_puc/{self.objects.ehp.pk}/')
        self.assertEqual(found.func, views.link_habitsandpractices)

    def test_product_surveyed_field(self):

        data = {'habits-TOTAL_FORMS':'2',
        'habits-INITIAL_FORMS':'1',
        'habits-MIN_NUM_FORMS':'0',
        'habits-MAX_NUM_FORMS':'1000',
        'habits-0-id': self.objects.ehp.pk,
        'habits-0-product_surveyed':'',
        }
        hp_formset = HnPFormSet(data, prefix='habits')
        self.assertFalse(hp_formset.is_valid())

        data = {'habits-TOTAL_FORMS':'2',
        'habits-INITIAL_FORMS':'1',
        'habits-MIN_NUM_FORMS':'0',
        'habits-MAX_NUM_FORMS':'1000',
        'habits-0-id': self.objects.ehp.pk,
        'habits-0-product_surveyed':'monster trucks',
        }
        hp_formset = HnPFormSet(data, prefix='habits')

        self.assertTrue(hp_formset.is_valid())
