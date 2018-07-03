from django.test import TestCase
from .loader import load_model_objects
from dashboard.models import ProductToPUC

class ModelsTest(TestCase):

    def setUp(self):
        self.objects = load_model_objects()

    def test_uber_puc(self):
        # Test that when the product has no assigned PUC, the getter returns
        # None
        self.assertTrue(self.objects.p.get_uber_product_to_puc() == None)

        self.ppuc = ProductToPUC.objects.create(product=self.objects.p,
                                        PUC=self.objects.puc,
                                        puc_assigned_usr=self.objects.user)

        # Test that the get_uber_product_to_puc method returns expected values
        uber_ppuc = self.objects.p.get_uber_product_to_puc()
        self.assertTrue(uber_ppuc.puc_assigned_usr.username == 'Karyn')
        uber_puc = self.objects.p.get_uber_puc()
        _str = 'Test General Category - Test Product Family - Test Product Type'
        self.assertEqual(_str, str(uber_puc)) # test str output
        uber_puc.prod_fam = None # test str output *w/o* prod_fam
        _str = 'Test General Category - Test Product Type'
        self.assertEqual(_str, str(uber_puc))
        uber_puc.gen_cat = None # test str output *w/o* gen_cat or prod_fam
        _str = 'Test Product Type'
        self.assertEqual(_str, str(uber_puc))
