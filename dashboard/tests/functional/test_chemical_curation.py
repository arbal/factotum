from django.test import TestCase
from dashboard.tests.loader import fixtures_standard
from dashboard.models import RawChem


class ChemicalCurationTests(TestCase):
    fixtures = fixtures_standard

    def setUp(self):
        self.client.login(username='Karyn', password='specialP@55word')

    def test_chemical_curation_page(self):
        """
        Ensure there is a chemical curation page
        :return: a 200 status code
        """
        response = self.client.get('/chemical_curation/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Download uncurated chemicals for a Data Group')

        # Pick one curated and one non-curated RawChem record, and
        # confirm that the downloaded file excludes and includes them,
        # respectively.
        rc = RawChem.objects.filter(dsstox_id__isnull=True).first()
        response = self.client.get('/dl_raw_chems/')
        header = 'dashboard_rawchem_id,raw_cas,raw_chem_name,rid,datagroup_id'
        self.assertEqual(header, str(response.content,'utf-8').split('\r\n')[0], "header fields should match")
        rc_row = f'{rc.id},{rc.raw_cas},{rc.raw_chem_name},{rc.rid if rc.rid else ""},{rc.data_group_id}'
        rc_row = bytes(rc_row, 'utf-8')
        self.assertIn(rc_row, response.content, 'The non-curated row should appear')
        rc = RawChem.objects.filter(dsstox_id__isnull=False).first()
        rc_row = f'{rc.id},{rc.raw_cas},{rc.raw_chem_name},{rc.rid if rc.rid else ""},{rc.data_group_id}'
        rc_row = bytes(rc_row, 'utf-8')
        self.assertNotIn(rc_row, response.content, 'The curated row should not appear')
