from lxml import html
from datetime import date
from django.test import TestCase, override_settings


from dashboard.models import (
    ExtractedHabitsAndPractices,
    ExtractedHabitsAndPracticesToTag,
    ExtractedHabitsAndPracticesTag,
    ExtractedHabitsAndPracticesTagKind,
)
from django.conf import settings
from dashboard.tests.loader import fixtures_standard, fixtures_habits_practices


@override_settings(ALLOWED_HOSTS=["testserver"])
class HabitsAndPracticesTest(TestCase):
    fixtures = fixtures_habits_practices
    # Data document 53 is a Habits & Practices doc

    def setUp(self):
        self.client.login(username="Karyn", password="specialP@55word")

    def test_hp_tags(self):
        # makes two new tags and assigns them to an existing ExtractedHabitsAndPractices
        hp1 = ExtractedHabitsAndPractices.objects.filter(extracted_text_id=53).first()
        kind1 = ExtractedHabitsAndPracticesTagKind(name="age group")
        kind1.save()
        tag1 = ExtractedHabitsAndPracticesTag(name="infant", kind=kind1)
        tag1.save()
        hp1.tags.add(tag1)
        kind2 = ExtractedHabitsAndPracticesTagKind(name="ethnicity")
        kind2.save()
        tag2 = ExtractedHabitsAndPracticesTag(name="non-hispanic white", kind=kind2)
        tag2.save()
        hp1.tags.add(tag2)
        # both tags are now related to the ExtractedHabitsAndPractices record
        self.assertEqual(hp1.tags.count(), 2)
        # one of the new tags has today's date for its updated_at
        self.assertEqual(hp1.tags.first().updated_at.day, date.today().day)
