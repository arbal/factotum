from django.test import TestCase

from dashboard.tests.loader import fixtures_standard
from dashboard.models import ExtractedText, DataDocument, Product


class ProductTest(TestCase):
    fixtures = fixtures_standard

    def test_rawchemlookup(self):
        # product with data document without extracted text
        et = ExtractedText.objects.values_list("pk", flat=True)
        dd = DataDocument.objects.exclude(pk__in=et)
        p = Product.objects.create(upc="1000000000000000")
        dd.first().products.add(p)
        rawchems = [r for r in p.rawchems]
        self.assertEqual(rawchems, [])
