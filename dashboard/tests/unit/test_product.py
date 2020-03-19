from django.test import TestCase

from dashboard.tests.loader import fixtures_standard
from dashboard.models import ExtractedText, DataDocument, ProductDocument, Product
from dashboard.tests.mixins import TempFileMixin


class ProductTests(TempFileMixin, TestCase):
    def test_image_upload(self):
        product = Product()
        product.image.save(
            name="dave_or_grant.png",
            content=open(
                "sample_files/images/products/product_image_upload_valid/dave_or_grant.png",
                "rb",
            ),
            save=True,
        )
        sample_file = open(
            "sample_files/images/products/product_image_upload_valid/dave_or_grant.png",
            "rb",
        )
        saved_image = product.image.open(mode="rb")
        # Verify binary data is identical
        self.assertEqual(saved_image.read(), sample_file.read())


class ProductTestWithSeedData(TestCase):

    fixtures = fixtures_standard

    def test_rawchemlookup(self):
        # product with data document without extracted text
        et = ExtractedText.objects.values_list("pk", flat=True)
        dd = DataDocument.objects.exclude(pk__in=et).values_list("pk", flat=True)
        pd = ProductDocument.objects.filter(
            document__in=dd, product__isnull=False
        ).values_list("product", flat=True)
        p = Product.objects.filter(pk__in=pd).first()
        rawchems = [r for r in p.rawchems]
        self.assertEqual(rawchems, [])
