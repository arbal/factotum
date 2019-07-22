from django.test import TestCase, tag

from dashboard.models import PUCTag, ProductToTag, PUCToTag
from dashboard.tests.loader import load_model_objects


@tag("loader")
class ProductToTagTest(TestCase):
    def setUp(self):
        self.objects = load_model_objects()

    def test_product_tag_insert(self):
        t = PUCTag.objects.create(name="tang", slug="tang")
        self.assertEqual(
            len(ProductToTag.objects.all()),
            0,
            ("There should be no Product linked to PUCTag"),
        )
        c = ProductToTag.objects.create(content_object=self.objects.p, tag=t)
        self.assertEqual(
            len(ProductToTag.objects.all()),
            1,
            ("There should be a Product linked to PUCTag"),
        )

    def test_puc_tag_insert(self):
        t = PUCTag.objects.create(name="tang", slug="tang")
        self.assertEqual(
            len(PUCToTag.objects.all()), 0, ("There should be no PUC linked to PUCTag")
        )
        c = PUCToTag.objects.create(content_object=self.objects.puc, tag=t)
        self.assertEqual(
            len(PUCToTag.objects.all()), 1, ("There should be a PUC linked to PUCTag")
        )
