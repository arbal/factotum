from django.db.utils import IntegrityError
from django.test import TestCase, tag

from dashboard.models import Product, PUC, ProductToPUC, ProductUberPuc, PUCKind
from dashboard.tests.loader import load_model_objects, fixtures_standard
from dashboard.views.product_curation import ProductForm

import time


@tag("puc")
class ProductToPUCTestWithSeedData(TestCase):
    fixtures = fixtures_standard

    def setUp(self):
        self.client.login(username="Karyn", password="specialP@55word")

    def test_uber_puc_update(self):
        # Test that when a product-to-puc record is deleted or added or updated,
        # the is_uber_puc attribute is reassigned to the correct row
        p = Product.objects.get(pk=1866)
        ptps = ProductToPUC.objects.filter(product=p)
        # print(
        #     ptps.values_list(
        #         "product_id", "puc_id", "classification_method_id", "is_uber_puc"
        #     )
        # )
        # delete the MA uber PUC
        ptps.filter(is_uber_puc=True).delete()
        # confirm that the MB PUC assignment has inherited the uber status
        ptp = ptps.get(is_uber_puc=True)
        self.assertTrue(ptp.classification_method_id == "MB")
        # reassign the 185 PUC as MA and confirm that it becomes the new uber PUC
        ProductToPUC.objects.create(
            product_id=1866, puc_id=185, classification_method_id="MA"
        )
        ptp = ptps.get(is_uber_puc=True)
        self.assertTrue(ptp.classification_method_id == "MA")


@tag("loader", "puc")
class ProductToPUCTest(TestCase):
    def setUp(self):
        self.objects = load_model_objects()

    def test_uber_puc_view(self):
        prod = self.objects.p
        # confirm that the new relationship returns None
        self.assertTrue(prod.product_uber_puc == None)

        # Create a three-part PUC hierarchy
        puc1 = PUC.objects.create(
            gen_cat="Grandparent gencat",
            prod_fam="",
            prod_type="",
            description="Grandparent",
            last_edited_by=self.objects.user,
            kind=PUCKind.objects.get_or_create(name="Formulation", code="FO")[0],
        )

        puc2 = PUC.objects.create(
            gen_cat="Grandparent gencat",
            prod_fam="Parent prodfam",
            prod_type="",
            description="Parent",
            last_edited_by=self.objects.user,
            kind=PUCKind.objects.get_or_create(name="Formulation", code="FO")[0],
        )

        # assign the Grandparent PUC as a low-confidence "AU" classification_method
        pp1 = ProductToPUC.objects.create(
            product=prod, puc=puc1, classification_method_id="AU"
        )
        prod.refresh_from_db()

        self.assertTrue(prod.product_uber_puc.puc == puc1)

        # assign a higher-confidence method and check the uber puc

        pp2 = ProductToPUC.objects.create(
            product=prod, puc=puc2, classification_method_id="MB"
        )
        prod.refresh_from_db()
        self.assertTrue(prod.product_uber_puc.puc == puc2)

    def test_uber_puc(self):
        # Test that when the product has no assigned PUC, the getter returns
        # None
        self.assertTrue(self.objects.p.uber_puc == None)

        self.ppuc = ProductToPUC.objects.create(
            product=self.objects.p,
            puc=self.objects.puc,
            puc_assigned_usr=self.objects.user,
            classification_method_id="MA",
        )

        # Test that the get_uber_product_to_puc method returns expected values
        uber_puc = self.objects.p.uber_puc
        _str = "Test General Category - Test Product Family - Test Product Type"
        self.assertEqual(_str, str(uber_puc))  # test str output
        uber_puc.prod_fam = None  # test str output *w/o* prod_fam
        _str = "Test General Category - Test Product Type"
        self.assertEqual(_str, str(uber_puc))
        uber_puc.gen_cat = None  # test str output *w/o* gen_cat or prod_fam
        _str = "Test Product Type"
        self.assertEqual(_str, str(uber_puc))

    def test_get_classification_method(self):
        # Test that when the product has no assigned classification method, the getter returns
        # None
        self.assertTrue(self.objects.p.get_classification_method == None)

        self.rule_based_ppuc = ProductToPUC.objects.create(
            product=self.objects.p,
            puc=self.objects.puc,
            puc_assigned_usr=self.objects.user,
            classification_method_id="RU",
        )

        self.manual_assignment_ppuc = ProductToPUC.objects.create(
            product=self.objects.p,
            puc=self.objects.puc,
            puc_assigned_usr=self.objects.user,
            classification_method_id="MA",
        )

        self.manual_batch_ppuc = ProductToPUC.objects.create(
            product=self.objects.p,
            puc=self.objects.puc,
            puc_assigned_usr=self.objects.user,
            classification_method_id="MB",
        )
        self.automatic_ppuc = ProductToPUC.objects.create(
            product=self.objects.p,
            puc=self.objects.puc,
            puc_assigned_usr=self.objects.user,
            classification_method_id="AU",
        )

        self.bulk_assignment_ppuc = ProductToPUC.objects.create(
            product=self.objects.p,
            puc=self.objects.puc,
            puc_assigned_usr=self.objects.user,
            classification_method_id="BA",
        )

        # Order of confidence:
        # "MA", "Manual"
        # "RU", "Rule Based"
        # "MB", "Manual Batch"
        # "BA", "Bulk Assignment"
        # "AU", "Automatic"

        # Five product-to-puc relationships created, the highest confidence should always be selected
        # Test that the get_classification_method method returns expected values
        classification_method = self.objects.p.get_classification_method
        _str = "Manual"
        # classification method should be Manual (highest confidence)
        self.assertEqual(_str, str(classification_method.name))

        self.manual_assignment_ppuc.delete()
        classification_method = self.objects.p.get_classification_method
        _str = "Rule Based"
        # classification method should be Rule Based since Manual was deleted
        self.assertEqual(_str, str(classification_method.name))

        self.rule_based_ppuc.delete()
        classification_method = self.objects.p.get_classification_method
        _str = "Manual Batch"
        # classification method should be Manual Batch since Rule Based was deleted
        self.assertEqual(_str, str(classification_method.name))

        self.manual_batch_ppuc.delete()
        classification_method = self.objects.p.get_classification_method
        _str = "Bulk Assignment"
        # classification method should be Bulk Assignment since Manual Batch was deleted
        self.assertEqual(_str, str(classification_method.name))

        self.bulk_assignment_ppuc.delete()
        classification_method = self.objects.p.get_classification_method
        _str = "Automatic"
        # classification method should be Automatic since Bulk Assignment was deleted
        self.assertEqual(_str, str(classification_method.name))

    # it seems to be necessary to use the __dict__ and instance in order to load
    # the form for testing, w/o I don't think the fields are bound, which will
    # never validate!
    def test_ProductForm_invalid(self):
        form = ProductForm(self.objects.p.__dict__, instance=self.objects.p)
        self.assertFalse(form.is_valid())

    def test_ProductForm_valid(self):
        self.objects.p.title = "Title Necessary"
        self.objects.p.upc = "Upc Necessary"
        self.objects.p.document_type = self.objects.dt.id
        self.objects.p.save()
        form = ProductForm(self.objects.p.__dict__, instance=self.objects.p)
        self.assertTrue(form.is_valid())

    def test_unique_constraint(self):
        self.ppuc1 = ProductToPUC.objects.create(
            product=self.objects.p,
            puc=self.objects.puc,
            puc_assigned_usr=self.objects.user,
            classification_method_id="MA",
        )

        with self.assertRaises(IntegrityError):
            self.ppuc2 = ProductToPUC.objects.create(
                product=self.objects.p,
                puc=self.objects.puc,
                puc_assigned_usr=self.objects.user,
                classification_method_id="MA",
            )
