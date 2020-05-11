from django.db.utils import IntegrityError
from django.test import TestCase, tag

from dashboard.models import ProductToPUC
from dashboard.tests.loader import load_model_objects
from dashboard.views.product_curation import ProductForm


@tag("loader")
class ProductToPUCTest(TestCase):
    def setUp(self):
        self.objects = load_model_objects()

    def test_uber_puc(self):
        # Test that when the product has no assigned PUC, the getter returns
        # None
        self.assertTrue(self.objects.p.uber_puc == None)

        self.ppuc = ProductToPUC.objects.create(
            product=self.objects.p,
            puc=self.objects.puc,
            puc_assigned_usr=self.objects.user,
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
            classification_method="RU",
        )

        self.manual_assignment_ppuc = ProductToPUC.objects.create(
            product=self.objects.p,
            puc=self.objects.puc,
            puc_assigned_usr=self.objects.user,
            classification_method="MA",
        )

        self.manual_batch_ppuc = ProductToPUC.objects.create(
            product=self.objects.p,
            puc=self.objects.puc,
            puc_assigned_usr=self.objects.user,
            classification_method="MB",
        )
        self.automatic_ppuc = ProductToPUC.objects.create(
            product=self.objects.p,
            puc=self.objects.puc,
            puc_assigned_usr=self.objects.user,
            classification_method="AU",
        )

        self.bulk_assignment_ppuc = ProductToPUC.objects.create(
            product=self.objects.p,
            puc=self.objects.puc,
            puc_assigned_usr=self.objects.user,
            classification_method="BA",
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
        self.assertEqual(_str, str(classification_method))

        self.manual_assignment_ppuc.delete()
        classification_method = self.objects.p.get_classification_method
        _str = "Rule Based"
        # classification method should be Rule Based since Manual was deleted
        self.assertEqual(_str, str(classification_method))

        self.rule_based_ppuc.delete()
        classification_method = self.objects.p.get_classification_method
        _str = "Manual Batch"
        # classification method should be Manual Batch since Rule Based was deleted
        self.assertEqual(_str, str(classification_method))

        self.manual_batch_ppuc.delete()
        classification_method = self.objects.p.get_classification_method
        _str = "Bulk Assignment"
        # classification method should be Bulk Assignment since Manual Batch was deleted
        self.assertEqual(_str, str(classification_method))

        self.bulk_assignment_ppuc.delete()
        classification_method = self.objects.p.get_classification_method
        _str = "Automatic"
        # classification method should be Automatic since Bulk Assignment was deleted
        self.assertEqual(_str, str(classification_method))

    # it seems to be necessary to us the __dict__ and instance in order to load
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

    def test_unique_constaint(self):
        self.ppuc1 = ProductToPUC.objects.create(
            product=self.objects.p,
            puc=self.objects.puc,
            puc_assigned_usr=self.objects.user,
        )

        with self.assertRaises(IntegrityError):
            self.ppuc2 = ProductToPUC.objects.create(
                product=self.objects.p,
                puc=self.objects.puc,
                puc_assigned_usr=self.objects.user,
            )
