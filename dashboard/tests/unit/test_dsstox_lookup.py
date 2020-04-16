from django.test import TestCase
from dashboard.models import (
    DSSToxLookup,
    ExtractedListPresence,
    ExtractedListPresenceTag,
    DataDocument,
    ExtractedText,
)
from dashboard.tests.loader import load_model_objects


class DSSToxLookupTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.loaded_objects = load_model_objects()

        cls.dsstox = DSSToxLookup.objects.create(
            sid="1", true_chemname="valid", true_cas="1"
        )
        cls.dsstox_2 = DSSToxLookup.objects.create(
            sid="2", true_chemname="invalid", true_cas="0"
        )

        cls.tag_1 = ExtractedListPresenceTag.objects.create(
            slug="abrasive", name="abrasive"
        )
        cls.tag_2 = ExtractedListPresenceTag.objects.create(
            slug="europe", name="europe"
        )

        # Create a list presence that should never be returned
        # by the self.dsstox.get_tags_with_extracted_text()
        elp = ExtractedListPresence.objects.create(
            extracted_text=cls.loaded_objects.extext
        )
        elp.rid = "RID0009999"
        elp.dsstox = cls.dsstox_2
        elp.tags.add(cls.tag_1)
        elp.save()

    def test_get_tags_with_extracted_text_single_elp(self):
        valid_elp = self._create_extracted_list_presences(
            1, self.loaded_objects.extext, tags=[self.tag_1]
        )

        tagsets = self.dsstox.get_tags_with_extracted_text()

        self.assertEqual(len(tagsets), 1, "Only 1 tag set should have been returned")
        self.assertSetEqual(tagsets[0]["tags"], {self.tag_1})
        self.assertEqual(
            len(tagsets[0]["related"]),
            1,
            "Only 1 related extracted text should have been returned",
        )
        self.assertEqual(
            tagsets[0]["related"][0]["extracted_text"], self.loaded_objects.extext
        )
        self.assertEqual(
            len(tagsets[0]["related"][0]["extracted_list_presence"]),
            1,
            "Only 1 related extracted list presence should have been returned",
        )
        self.assertEqual(
            tagsets[0]["related"][0]["extracted_list_presence"][0], valid_elp[0]
        )

    def test_get_tags_with_extracted_text_multiple_elps(self):
        valid_elp = self._create_extracted_list_presences(
            2, self.loaded_objects.extext, tags=[self.tag_1]
        )

        tagsets = self.dsstox.get_tags_with_extracted_text()

        self.assertEqual(len(tagsets), 1, "Only 1 tag set should have been returned")
        self.assertSetEqual(tagsets[0]["tags"], {self.tag_1})
        self.assertEqual(
            len(tagsets[0]["related"]),
            1,
            "Only 1 related extracted text should have been returned",
        )
        self.assertEqual(
            tagsets[0]["related"][0]["extracted_text"], self.loaded_objects.extext
        )
        self.assertEqual(
            len(tagsets[0]["related"][0]["extracted_list_presence"]),
            2,
            "2 related extracted list presence should have been returned",
        )
        self.assertListEqual(
            tagsets[0]["related"][0]["extracted_list_presence"], valid_elp
        )

    def test_get_tags_with_extracted_text_multiple_elps_different_tags(self):
        valid_elp = self._create_extracted_list_presences(
            1, self.loaded_objects.extext, tags=[self.tag_1]
        )
        valid_elp += self._create_extracted_list_presences(
            1, self.loaded_objects.extext, tags=[self.tag_1, self.tag_2]
        )

        tagsets = self.dsstox.get_tags_with_extracted_text()

        self.assertEqual(len(tagsets), 2, "2 tag sets should have been returned")
        for tagset in tagsets:
            self.assertIn(tagset["tags"], [{self.tag_1}, {self.tag_1, self.tag_2}])
            self.assertEqual(
                len(tagset["related"]),
                1,
                "Only 1 related extracted text should have been returned",
            )
            self.assertEqual(
                tagset["related"][0]["extracted_text"], self.loaded_objects.extext
            )
            self.assertEqual(
                len(tagset["related"][0]["extracted_list_presence"]),
                1,
                "Only 1 related extracted list presence should have been returned",
            )
            self.assertIn(
                tagset["related"][0]["extracted_list_presence"][0], set(valid_elp)
            )

    def test_get_tags_with_extracted_text_multiple_elps_different_extracted_texts(self):
        dd = DataDocument.objects.create(data_group=self.loaded_objects.dg)
        et = ExtractedText.objects.create(
            data_document=dd, extraction_script=self.loaded_objects.script
        )
        valid_elp = self._create_extracted_list_presences(
            1, self.loaded_objects.extext, tags=[self.tag_1]
        )
        valid_elp += self._create_extracted_list_presences(1, et, tags=[self.tag_1])

        tagsets = self.dsstox.get_tags_with_extracted_text()

        self.assertEqual(len(tagsets), 1, "Only 1 tag set should have been returned")
        self.assertSetEqual(tagsets[0]["tags"], {self.tag_1})
        self.assertEqual(
            len(tagsets[0]["related"]),
            2,
            "2 related extracted text should have been returned",
        )
        self.assertListEqual(
            [related["extracted_text"] for related in tagsets[0]["related"]],
            [self.loaded_objects.extext, et],
        )
        flat_elps = [
            elp
            for sublist in tagsets[0]["related"]
            for elp in sublist["extracted_list_presence"]
        ]
        self.assertListEqual(flat_elps, valid_elp)

    def test_get_tags_with_extracted_text_filters_tag_id(self):
        valid_elp = self._create_extracted_list_presences(
            1, self.loaded_objects.extext, tags=[self.tag_1, self.tag_2]
        )
        # Create list presences to be filtered
        self._create_extracted_list_presences(
            1, self.loaded_objects.extext, tags=[self.tag_1]
        )

        tagsets = self.dsstox.get_tags_with_extracted_text(tag_id=self.tag_2.pk)

        self.assertEqual(len(tagsets), 1, "Only 1 tag set should have been returned")
        self.assertSetEqual(tagsets[0]["tags"], {self.tag_1, self.tag_2})
        self.assertEqual(
            len(tagsets[0]["related"]),
            1,
            "Only 1 related extracted text should have been returned",
        )
        self.assertEqual(
            tagsets[0]["related"][0]["extracted_text"], self.loaded_objects.extext
        )
        self.assertEqual(
            len(tagsets[0]["related"][0]["extracted_list_presence"]),
            1,
            "Only 1 related extracted list presence should have been returned",
        )
        self.assertEqual(
            tagsets[0]["related"][0]["extracted_list_presence"][0], valid_elp[0]
        )

    def test_get_tags_with_extracted_text_filters_doc_id(self):
        dd = DataDocument.objects.create(data_group=self.loaded_objects.dg)
        et = ExtractedText.objects.create(
            data_document=dd, extraction_script=self.loaded_objects.script
        )
        valid_elp = self._create_extracted_list_presences(
            1, self.loaded_objects.extext, tags=[self.tag_1]
        )
        # Add extracted list presences to be filtered
        self._create_extracted_list_presences(1, et, tags=[self.tag_1])

        tagsets = self.dsstox.get_tags_with_extracted_text(
            doc_id=self.loaded_objects.extext.data_document_id
        )

        self.assertEqual(len(tagsets), 1, "Only 1 tag set should have been returned")
        self.assertSetEqual(tagsets[0]["tags"], {self.tag_1})
        self.assertEqual(
            len(tagsets[0]["related"]),
            1,
            "Only 1 related extracted text should have been returned",
        )
        self.assertEqual(
            tagsets[0]["related"][0]["extracted_text"], self.loaded_objects.extext
        )
        self.assertEqual(
            len(tagsets[0]["related"][0]["extracted_list_presence"]),
            1,
            "Only 1 related extracted list presence should have been returned",
        )
        self.assertEqual(
            tagsets[0]["related"][0]["extracted_list_presence"][0], valid_elp[0]
        )

    def _create_extracted_list_presences(self, count, extracted_text, tags=None):
        created_elps = []
        for i in range(count):
            elp = ExtractedListPresence.objects.create(extracted_text=extracted_text)
            elp.rid = "RID000" + str(i)
            elp.dsstox = self.dsstox
            for tag in tags:
                elp.tags.add(tag)
            elp.save()
            created_elps.append(elp)
        return created_elps
