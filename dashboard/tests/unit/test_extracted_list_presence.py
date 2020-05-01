from django.test import TestCase

from dashboard.tests.factories import (
    ExtractedListPresenceTagFactory,
    ExtractedListPresenceFactory,
)


class ExtractedListPresenceTagTest(TestCase):
    fixtures = ["00_superuser"]

    @classmethod
    def setUpTestData(cls):
        cls.tags = ExtractedListPresenceTagFactory.create_batch(2)
        # Make 2 extracted list presences with different
        # one with tags [tags[0]] and one with tags [tags[0],tags[1]]
        cls.elp_first_tag = ExtractedListPresenceFactory(tags=[cls.tags[0]])
        cls.elp_all_tags = ExtractedListPresenceFactory(tags=cls.tags)
        cls.elp_duplicate = ExtractedListPresenceFactory(tags=cls.tags)

    def test_get_tagsets_returns_all_tagsets(self):
        expected_tagsets = [tuple([self.tags[0], self.tags[1]]), tuple([self.tags[0]])]
        tagsets = self.tags[0].get_tagsets()

        self._assert_tagsets_equal(tagsets, expected_tagsets)

    def test_get_tagsets_filters_tagsets_without_tag(self):
        expected_tagsets = [tuple([self.tags[0], self.tags[1]])]
        tagsets = self.tags[1].get_tagsets()

        self._assert_tagsets_equal(tagsets, expected_tagsets)

    def test_get_tagsets_tag_never_used(self):
        tagsets = ExtractedListPresenceTagFactory().get_tagsets()
        self.assertEqual(len(tagsets), 0, "Unused tags should return no tagsets")

    def _assert_tagsets_equal(self, tagsets, expected_tagsets):
        self.assertEqual(
            len(tagsets),
            len(expected_tagsets),
            f"There should be {len(expected_tagsets)} tag set returned.",
        )
        for expected_tagset in expected_tagsets:
            self.assertIn(expected_tagset, tagsets)
