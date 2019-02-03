import django
import os
import warnings
import csv

# Ignore this specific warning.  It is not crucial to use the Levenshtein library for this script.
warnings.filterwarnings("ignore", message="Using slow pure-python SequenceMatcher. Install python-Levenshtein to remove this warning")

from django.core.management.base import BaseCommand

# settings need setup before calling any Django code
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "factotum.settings")
django.setup()

from dashboard.models import Product

# Import the fuzzywuzzy package/libraries.
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

from pathlib import Path

class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        help = 'Score stub product titles'

        # Get all the products that have stub UPCs.
        stub_products = Product.objects.filter(upc__contains="stub")

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

        # Set up pathnames for output files.
        top_match_pathname = Path.cwd().joinpath('top_match.csv')
        multi_match_pathname = Path.cwd().joinpath('multi_matches.csv')

        # Open file that will contain the top match for each stub product
        top_match_csv = Path.open(top_match_pathname, mode="w", newline='')

        # Open file that will contain matching scores for the process.extract method
        multi_match_csv = Path.open(multi_match_pathname, mode="w", newline='')

        # Set the number of matches ordered by scores.  By default this number is 5.
        num_matches = 3

        # Set the threshold value to use for the matching score.  This value will be used for each stub product
        # that is compared to every UPC product. Adjust this parameter to a desired threshold. This parameter has
        # a default value of 0 if not set by the user.  Matching scores below this value will not appear in the results.
        cutoff = 80

        # Build CSV headers.  Attach indices to headers to make them unique.
        top_match_headers = ['stub product', 'pk_stub', 'upc product', 'pk_upc', 'score']
        multi_match_headers = ['stub product', 'pk_stub']
        for i in range(num_matches):
            str1 = 'upc product' + str(i+1)
            str2 = 'pk_upc' + str(i+1)
            str3 = 'score' + str(i+1)
            multi_match_headers.extend((str1, str2, str3))

        # Create writer objects that will map dictionaries to onto output rows.
        top_match_writer = csv.DictWriter(top_match_csv, top_match_headers)
        multi_match_writer = csv.DictWriter(multi_match_csv, multi_match_headers)

        # Write headers
        top_match_writer.writeheader()
        multi_match_writer.writeheader()

        # Loop through stubs
        for stub_product in stub_products:
            # Find title and compare it to every non-stub product.
            stub_prod1 = stub_product.title.lower()
            stub_prod = stub_prod1.replace(":", "").replace("\t", "").replace(",", "")
            stub_prod_pk = stub_product.pk

            # Initialize stub product string that will be used for the YAML strings below.
            top_match_dict = {'stub product': stub_prod, 'pk_stub': stub_prod_pk}
            multi_match_dict = {'stub product': stub_prod, 'pk_stub': stub_prod_pk}

            # Get a list of matches ordered by scores, using the fuzz.token_set_ratio matching , to get all num_matches.
            # Note:  there are 4 popular types of fuzzy matching logic supported by the fuzzywuzzy package.  They are:
            # ratio, partial ratio, token sort ratio, and token set ratio.  Opted to use the token set ratio because it
            # gives me the best scores and matches.  That said, the user can set the scorer to any other matching method
            # if wished.
            multi_match_list = process.extract(stub_prod, list_upc_names, scorer=fuzz.token_set_ratio, limit=num_matches)

            # Convert list to a dictionary.
            multi_dict = dict(multi_match_list)

            # Set counter of upc products to minus one.
            j = -1

            # Loop over items in dictionary and build dictionary for output.
            for key, value in multi_dict.items():
                i_upc = list_upc_names.index(key)                     # Locate upc name in original list.
                j = j + 3
                new_key = key.replace(":", "").replace("\t", "").replace(",", "")
                multi_match_dict[multi_match_headers[j]] = new_key
                multi_match_dict[multi_match_headers[j+1]] = list_upc_pks[i_upc]
                multi_match_dict[multi_match_headers[j+2]] = value

            # Write row of data.
            multi_match_writer.writerow(multi_match_dict)

            # Get the top one match, using the fuzz.token_set_ratio matching and a threshold value.
            top_match_list = process.extractOne(stub_prod, list_upc_names, scorer=fuzz.token_set_ratio, score_cutoff=cutoff)

            # Check whether a match was found.  If a match is not found, print appropriate message to output.
            # If match is found, add upc product name, pk id, and score to dictionary.
            if top_match_list is None:
                top_match_dict[top_match_headers[2]] = 'No match was found.'
                top_match_dict[top_match_headers[3]] = 'NA'
                top_match_dict[top_match_headers[4]] = 'NA'
            else:
                i_upc = list_upc_names.index(top_match_list[0])
                top_match_dict[top_match_headers[2]] = top_match_list[0]
                top_match_dict[top_match_headers[3]] = list_upc_pks[i_upc]
                top_match_dict[top_match_headers[4]] = str(top_match_list[1])

            # Write row of data.
            top_match_writer.writerow(top_match_dict)

        # Write top match results to output file.
        print("Top match results were output to " + top_match_csv.name)

        # Write multiple matches results to output file.
        print("Multiple results were output to " + multi_match_csv.name)

        # Close files
        top_match_csv.close()
        multi_match_csv.close()
