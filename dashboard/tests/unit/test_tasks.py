import os
import shutil

from django.test import TestCase

from dashboard.tests import factories
from dashboard.tests.factories import ExtractedCompositionFactory
from dashboard.tasks import provisional_sid_assignment, generate_bulk_download_file
from factotum.settings import CSV_STORAGE_ROOT


class ProvisionalSidAssignmentTest(TestCase):
    def test_curates_rawchems(self):
        # Build data
        base_chem = ExtractedCompositionFactory()
        target = ExtractedCompositionFactory(
            is_curated=False,
            raw_chem_name=base_chem.raw_chem_name,
            raw_cas=base_chem.raw_cas,
        )
        target2 = ExtractedCompositionFactory(
            is_curated=False,
            raw_chem_name=base_chem.raw_chem_name,
            raw_cas=base_chem.raw_cas,
        )

        # These chems will remain uncurated due to not matching criteria
        uncurated_chems = []
        uncurated_chems.append(
            ExtractedCompositionFactory(
                is_curated=False, raw_chem_name=base_chem.raw_chem_name
            )
        )
        uncurated_chems.append(
            ExtractedCompositionFactory(is_curated=False, raw_cas=base_chem.raw_cas)
        )
        uncurated_chems.append(ExtractedCompositionFactory(is_curated=False))

        # Begin "Testing"
        self.assertIsNone(target.dsstox_id)

        provisional_sid_assignment.apply()

        target.refresh_from_db()
        target2.refresh_from_db()
        self.assertEqual(base_chem.dsstox_id, target.dsstox_id)
        self.assertEqual(base_chem.dsstox_id, target2.dsstox_id)

        for chem in uncurated_chems:
            chem.refresh_from_db()
            self.assertIsNone(chem.dsstox)

    def test_conflicts_not_curated(self):
        """If there are multiple different dsstox linked to the chem name and cas set
        no provisional curation occurs.
        """
        # Conflicting Set #
        # Base Chem
        base_chem = ExtractedCompositionFactory()
        # Conflicting chem
        ExtractedCompositionFactory(
            raw_chem_name=base_chem.raw_chem_name, raw_cas=base_chem.raw_cas
        )
        # Uncurated target
        target = ExtractedCompositionFactory(
            is_curated=False,
            raw_chem_name=base_chem.raw_chem_name,
            raw_cas=base_chem.raw_cas,
        )

        provisional_sid_assignment.apply()

        target.refresh_from_db()
        # Conflicts are not curated.
        self.assertIsNone(target.dsstox)

    def test_duplicate_non_conflicting_dsstox_curated(self):
        """If there are multiple of the same dsstox linked to the chem name and cas set
        provisional curation occurs as normal.
        """
        # Non-Conflicting Set #
        # Base Chem
        base_chem = ExtractedCompositionFactory()
        # Non-Conflicting chem
        ExtractedCompositionFactory(
            raw_chem_name=base_chem.raw_chem_name,
            raw_cas=base_chem.raw_cas,
            dsstox=base_chem.dsstox,
        )
        # Uncurated target
        target = ExtractedCompositionFactory(
            is_curated=False,
            raw_chem_name=base_chem.raw_chem_name,
            raw_cas=base_chem.raw_cas,
        )

        provisional_sid_assignment.apply()

        target.refresh_from_db()
        # Curation Completed.
        self.assertEqual(target.dsstox, base_chem.dsstox)
        self.assertTrue(target.provisional)


class GenerateBulkDownloadTest(TestCase):
    def test_generate_bulk_download_file(self):
        # clear files
        path = CSV_STORAGE_ROOT
        if os.path.exists(path):
            shutil.rmtree(path)
        # invoke task
        factories.ExtractedCompositionFactory.create_batch(500)
        generate_bulk_download_file.apply()
        # verify files generated
        self.assertTrue(os.path.exists(os.path.join(path, "composition_chemicals.csv")))
        self.assertTrue(os.path.exists(os.path.join(path, "composition_chemicals.zip")))
