from django.test import TestCase
from dashboard.tests.loader import fixtures_standard
from dashboard.models import RawChem, DSSToxLookup


class ChemicalCurationTests(TestCase):
    fixtures = fixtures_standard

    def setUp(self):
        self.client.login(username="Karyn", password="specialP@55word")

    def test_chemical_curation_page(self):
        """
        Ensure there is a chemical curation page
        :return: a 200 status code
        """
        response = self.client.get("/chemical_curation/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Download uncurated chemicals for a Data Group")

        # Pick one curated and one non-curated RawChem record, and
        # confirm that the downloaded file excludes and includes them,
        # respectively.
        rc = RawChem.objects.filter(dsstox_id__isnull=True).first()
        dg = rc.extracted_text.data_document.data_group
        response = self.client.get(f"/dl_raw_chems_dg/{dg.id}", follow=True)
        header = "id,raw_cas,raw_chem_name,rid,datagroup_id\n"

        resp = list(response.streaming_content)
        response_header = resp[0].decode("utf-8")
        self.assertEqual(
            header, response_header.split("\r\n")[0], "header fields should match"
        )

        rc_row = f'{rc.id},{rc.raw_cas},{rc.raw_chem_name},{rc.rid if rc.rid else ""},{rc.data_group_id}'
        self.assertIn(
            bytes(rc_row, "utf-8"),
            b"\t".join(resp),
            "The non-curated row should appear",
        )

        rc = RawChem.objects.filter(dsstox_id__isnull=False).first()
        dg = rc.extracted_text.data_document.data_group
        response = self.client.get(f"/dl_raw_chems_dg/{dg.id}/", follow=True)
        resp = list(response.streaming_content)
        rc = RawChem.objects.filter(dsstox_id__isnull=False).first()
        rc_row = f'{rc.id},{rc.raw_cas},{rc.raw_chem_name},{rc.rid if rc.rid else ""},{rc.data_group_id}'
        self.assertNotIn(
            bytes(rc_row, "utf-8"),
            b"\t".join(resp),
            "The curated row should not appear",
        )

    def test_chemical_curation_upload(self):
        true_chemname = "Terpenes and Terpenoids, mixed sour and sweet Orange-oil"
        self.assertEqual(
            0,
            DSSToxLookup.objects.filter(true_chemname=true_chemname).count(),
            "No matching true_chemname should exist",
        )
        with open("./sample_files/chemical_curation_upload.csv") as csv_file:
            response = self.client.post("/chemical_curation/", {"csv_file": csv_file})
        self.assertEqual(
            1,
            DSSToxLookup.objects.filter(true_chemname=true_chemname).count(),
            "Now a matching true_chemname should exist",
        )
