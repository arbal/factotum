import django
import os
import warnings

# Ignore this specific warning.  It is not crucial to use the Levenshtein library for this test.
warnings.filterwarnings("ignore",message="Using slow pure-python SequenceMatcher. Install python-Levenshtein to remove this warning")

# settings need setup before calling any Django code
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "factotum.settings")
django.setup()

from django.test import TestCase
from dashboard.models import Product

# Import the fuzzywuzzy package/libraries.
from fuzzywuzzy import fuzz
from fuzzywuzzy import process


class TestProductDupCheck(TestCase):

    def setUp(self):
        # Create a variable that will have all products that have non-stub UPCs.
        norm_products = Product.objects.exclude(upc__contains="stub")

        # Build list of UPC product names
        list_upc_names = []
        list_upc_pks = []
        for norm_product in norm_products:
            norm_prod = norm_product.title.lower()
            list_upc_names.append(norm_prod)
            pk_product = norm_product.pk
            list_upc_pks.append(pk_product)


    def test_top_match(self):
        stub_product = "fastset anchoring epoxy, high strength anchoring epoxy, dot anchoring"
        upc_product = "fastset anchoring epoxy, high strength epoxy, dot anchoring epoxy"
        cutoff = 80

        # Get the top one match, using the fuzz.token_set_ratio matching and a threshold value.
        list_one = process.extractOne(stub_product, list_upc_names, scorer=fuzz.token_set_ratio, score_cutoff=cutoff)
        upc_prod_match = list_one[0]
        self.assertEqual(upc_prod_match, upc_product)

    def test_multi_match(self):
        stub_product = "okeeffes working hand cream"
        upc_product = ["goof off professional strength voc compliant", \
                       "softsoap liquid hand soap lavender & chamomile", \
                       "dap alex plus acrylic latex caulk plus silicone"]

        # Set the number of matches ordered by scores.  By default this number is 5.
        num_matches = 3

        # Get a list of matches ordered by scores, using the fuzz.token_set_ratio matching , to get all num_matches.
        list_multi = process.extract(stub_product, list_upc_names, scorer=fuzz.token_set_ratio, limit=num_matches)

        for i in range(num_matches):
            upc_prod_match = list_multi[i][0]
            self.assertEqual(upc_prod_match, upc_product[i])