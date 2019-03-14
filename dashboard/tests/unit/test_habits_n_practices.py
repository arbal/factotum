from django.urls import resolve
from django.test import TestCase
from django.http import HttpRequest

from lxml import html

from dashboard import views
from dashboard.models import *
from dashboard.forms import create_detail_formset
from dashboard.tests.loader import load_model_objects



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
        self.objects.gt.code = 'HP'
        self.objects.gt.save()
        _, HnPFormSet = create_detail_formset(self.objects.doc)
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

    def test_edit_hnp_detail(self):
        self.objects.exscript.title = 'Manual (dummy)'
        self.objects.exscript.save()
        self.client.login(username='Karyn', password='specialP@55word')
        pk = self.objects.doc.pk
        response = self.client.get(f'/habitsandpractices/{pk}/')
        self.assertNotContains(response, 'Raw Category', html=True)

        # Ensure there are Cancel and Back buttons with the correct URL to return to the DG detail page
        self.assertContains(response, f'href="/datagroup/{self.objects.dg.pk}/" role="button">Cancel</a>')
        self.assertContains(response, f'href="/datagroup/{self.objects.dg.pk}/" role="button">Back</a>')

        # Ensure that the URL above responds correctly
        response2 = self.client.get(f'/datagroup/{self.objects.dg.pk}/')
        self.assertContains(response2, 'Data Group Detail: Data Group for Test')
