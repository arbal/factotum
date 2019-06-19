from lxml import html

from django.test import TestCase

from dashboard.models import DSSToxLookup, ProductDocument, PUC, ProductToPUC
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
        
        pdocs = ProductDocument.objects.from_chemical(dss)
        first_puc_id = PUC.objects.filter(products__in=pdocs.values('product')).first().id

        self.assertContains(response, f'a href="/puc/{first_puc_id}')
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
        
        # Confirm that the list is displaying unique PUCs:
        # Set all the Ethylparaben-linked ProductToPuc relationships to a single PUC
        dss = DSSToxLookup.objects.get(sid='DTXSID9022528')
        ep_prods = ProductDocument.objects.from_chemical(dss).values_list('product_id')
        ProductToPUC.objects.filter(product_id__in=ep_prods).update(puc_id=210)

        response = self.client.get(f'/dsstox/{dss.sid}/')
        self.assertEqual(1, len(response.context['pucs']),
                            f'DSSTox pk={dss.pk} should return 1 '
                             'PUC in the context')

    def test_puc_bubble_query(self):
        dss = next(dss for dss in DSSToxLookup.objects.all() if dss.puc_count>0)
        response = self.client.get(f'/dl_pucs/?bubbles=True&dtxsid={dss.sid}')
        self.assertEqual(dss.puc_count, sum(1 for line in response) - 2,
                            f'DSSTox pk={dss.pk} should have {dss.puc_count} '
                             'PUCs in the CSV')

