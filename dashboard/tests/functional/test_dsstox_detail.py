from lxml import html

from django.test import TestCase

from dashboard.models import DSSToxLookup, ProductDocument, PUC
from dashboard.tests.loader import fixtures_standard


class DSSToxDetail(TestCase):

    fixtures = fixtures_standard

    def setUp(self):
        self.client.login(username='Karyn', password='specialP@55word')

    def test_dsstox_detail(self):
        dss = next(dss for dss in DSSToxLookup.objects.all() if dss.puc_count>0)
        response = self.client.get(f'/dsstox/{dss.sid}/')
        self.assertEqual(dss.puc_count, len(response.context['pucs']),
                            f'DSSTox pk={dss.pk} should have {dss.puc_count} '
                             'PUCs in the context')
        link = ('https://comptox.epa.gov/dashboard/dsstoxdb/results?search='
                f'{dss.sid}')
        self.assertContains(response, link)
        pdocs = ProductDocument.objects.from_chemical(dss)
        puc = PUC.objects.filter(products__in=pdocs.values('product')).first()
        self.assertContains(response, str(puc))
        dss = next(dss for dss in DSSToxLookup.objects.all() if dss.puc_count<1)
        response = self.client.get(f'/dsstox/{dss.sid}/')
        self.assertEqual(dss.puc_count, len(response.context['pucs']),
                            f'DSSTox pk={dss.pk} should have {dss.puc_count} '
                             'PUCs in the context')
        self.assertContains(response, 'No PUCs are linked to this chemical')


