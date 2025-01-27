import json

from django.urls import reverse
from lxml import html

from django.test import TestCase, tag, TransactionTestCase

from dashboard.models import DSSToxLookup, ProductDocument, PUC, ProductToPUC
from dashboard.tests.loader import fixtures_standard

from django.test import override_settings
from django.db import transaction

from dashboard.tests.factories import (
    ExtractedLMRecFactory,
    ExtractedHHRecFactory,
    TrueChemicalFactory,
    DataDocumentFactory,
)
from dashboard.tests.loader import load_model_objects
from dashboard.models import UnionExtractedLMHHRec


@tag("factory")
class LMRecTests(TransactionTestCase):
    """
    This test uses factories instead of the fixtures
    """

    def setUp(self):
        self.objects = load_model_objects()

        self.client.login(username="Karyn", password="specialP@55word")

        true_chem = TrueChemicalFactory.create(
            sid="DTXSID70452491", true_chemname="Benzene", true_cas="32501-94-3"
        )
        # Create data documents of both types
        lmdocs = DataDocumentFactory.create_batch(10, data_group__group_type__code="LM")
        hhdocs = DataDocumentFactory.create_batch(10, data_group__group_type__code="HH")

        # populate each document with chemical records, one of which is curated to the truechem
        for hhdoc in hhdocs:
            ExtractedHHRecFactory(extracted_text__data_document=hhdoc, dsstox=true_chem)
            ExtractedHHRecFactory.create_batch(
                10, extracted_text__data_document=hhdoc, is_curated=False
            )

        for lmdoc in lmdocs:
            ExtractedLMRecFactory(extracted_text__data_document=lmdoc, dsstox=true_chem)
            ExtractedLMRecFactory.create_batch(
                10, extracted_text__data_document=lmdoc, is_curated=False
            )

    def test_lm_hh_union_queryset(self):
        # true_chem = DSSToxLookup.objects.get(sid='DTXSID70452491')

        chem_table_qs = UnionExtractedLMHHRec.objects.filter(
            rawchem__dsstox__sid="DTXSID70452491"
        )

        self.assertEqual("DTXSID70452491", chem_table_qs.first().rawchem.dsstox.sid)
        self.assertEqual(20, chem_table_qs.count())

    def test_lmhh_table(self):
        dss = DSSToxLookup.objects.get(sid="DTXSID70452491")
        response = self.client.get(dss.get_absolute_url())
        self.assertContains(response, 'Products Containing "Benzene"')

        response = self.client.get(f"/lmhh_sid_json/?sid={dss.sid}")
        data = json.loads(response.content)
        self.assertEqual(
            data["recordsTotal"],
            20,
            f"DSSTox pk={dss.pk} should have 20 total records in the JSON",
        )


@override_settings(CACHEOPS_ENABLED=False)
@tag("puc")
class ChemicalDetail(TestCase):

    fixtures = fixtures_standard

    def setUp(self):
        self.client.login(username="Karyn", password="specialP@55word")

    def test_chemical_detail(self):
        # only test DSSToxLookup records that relate to PUCs
        sids_with_pucs = DSSToxLookup.objects.filter(
            curated_chemical__extracted_text__data_document__product__product_uber_puc__isnull=False
        )
        dss = next(dss for dss in sids_with_pucs)
        dsspuccount = dss.get_cumulative_puc_count()
        response = self.client.get(dss.get_absolute_url())
        self.assertEqual(
            dsspuccount,
            len(response.context["pucs"]),
            f"DSSTox pk={dss.pk} needs {dsspuccount} PUCs in the context",
        )

        pdocs = ProductDocument.objects.from_chemical(dss)
        first_puc_id = (
            PUC.objects.filter(products__in=pdocs.values("product")).first().id
        )

        self.assertContains(response, f'a href="/puc/{first_puc_id}')
        link = "https://comptox.epa.gov/dashboard/dsstoxdb/results?search=" f"{dss.sid}"
        self.assertContains(response, link)
        dss = next(dss for dss in DSSToxLookup.objects.all() if dss.get_puc_count() < 1)
        dsspuccount = dss.get_puc_count()
        response = self.client.get(dss.get_absolute_url())
        self.assertEqual(
            dsspuccount,
            len(response.context["pucs"]),
            f"DSSTox pk={dss.pk} needs {dsspuccount} PUCs in the context",
        )
        self.assertContains(response, "No PUCs are linked to this chemical")

        # Confirm that the list is displaying unique PUCs:
        # Set all the Ethylparaben-linked ProductToPuc relationships to a single PUC
        dss = DSSToxLookup.objects.get(sid="DTXSID9022528")
        dsspuccount = dss.get_puc_count()
        ep_prods = ProductDocument.objects.from_chemical(dss).values_list("product_id")
        ProductToPUC.objects.filter(product_id__in=ep_prods).update(puc_id=210)

        response = self.client.get(dss.get_absolute_url())
        self.assertEqual(
            dsspuccount,
            len(response.context["pucs"]),
            f"DSSTox pk={dss.pk} should return {dsspuccount} for the tree",
        )

        # Check cumulative product count
        pucs = PUC.objects.dtxsid_filter("DTXSID6026296").filter(
            gen_cat="Arts and Crafts/Office supplies"
        )
        cumulative_sum = sum(puc.product_count for puc in pucs)
        response_for_water = self.client.get("/chemical/DTXSID6026296/")
        self.assertEqual(
            cumulative_sum,
            response_for_water.context["pucs"]
            .children[0]
            .value.cumulative_product_count,
            f'Water sid ("DTXSID6026296") should have {cumulative_sum} associated products '
            + f"but returns {response_for_water.context['pucs'].children[0].value.cumulative_product_count}",
        )

    def _n_children(self, children):
        cnt = sum(1 for c in children if "value" in c)
        for c in children:
            if "children" in c:
                cnt += self._n_children(c["children"])
        return cnt

    def test_puc_bubble_query(self):
        """
        The JSON root should have as many children as there are PUCs with cumulative_product_count > 0
        """
        dss = next(dss for dss in DSSToxLookup.objects.all() if dss.get_puc_count() > 0)
        response = self.client.get(f"/dl_pucs_json/?kind=FO&dtxsid={dss.sid}")
        d = json.loads(response.content)

        self.assertEqual(
            dss.get_cumulative_puc_count(),
            self._n_children(d["children"]),
            f"DSSTox pk={dss.pk} should have {dss.get_cumulative_puc_count} PUCs in the JSON",
        )

    def test_cp_keyword_set(self):
        dss = DSSToxLookup.objects.get(sid="DTXSID9020584")
        response = self.client.get(dss.get_absolute_url())
        self.assertEqual(
            len(response.context["keysets"]),
            4,
            f"DSSTox pk={dss.pk} should return 4 CP keyword sets in the context",
        )

        for keyset in response.context["keysets"]:
            self.assertEqual(
                keyset.count,
                1,
                f"DSSTox pk={dss.pk} should keyword sets should all have 1 document associated with them",
            )

    def test_anonymous_read(self):
        self.client.logout()
        response = self.client.get("/chemical/DTXSID6026296/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Water")
        self.assertContains(response, "download_co_chemical")
        self.assertContains(response, "download products and weight fractions")

    def test_product_table(self):
        dss = DSSToxLookup.objects.get(sid="DTXSID6026296")
        response = self.client.get(dss.get_absolute_url())
        self.assertContains(response, 'Products Containing "water"')

        response_html = html.fromstring(response.content)
        datatable_sid = response_html.xpath('//*[@id="chemical"]/@data-sid')[0]
        self.assertEqual(dss.sid, datatable_sid, "Chemical sid incorrect")

        response = self.client.get(
            f"/chemical_product_json/?sid={dss.sid}&search[value]=Creme"
        )
        data = json.loads(response.content)
        self.assertEqual(
            data["recordsTotal"],
            6,
            f"DSSTox pk={dss.pk} should have 6 total records in the JSON",
        )
        self.assertEqual(
            data["recordsFiltered"],
            2,
            f'DSSTox pk={dss.pk} should have 2 records matching the search "Creme" in the JSON',
        )
        self.assertEqual(
            '<span title="formulation kind">Formulation</span>', data["data"][0][3]
        )
        self.assertEqual(
            '<span title="manually assigned">Manual</span>', data["data"][0][4]
        )

    def test_download_composition_chemical(self):
        self.client.logout()
        response = self.client.get(
            reverse("download_composition_chemical", args=["DTXSID6026296"])
        )
        self.assertEqual(response.status_code, 200)
        content = response.get("Content-Disposition")
        self.assertTrue(content.startswith("attachment; filename=dtxsid6026296"))

    def test_chemical_functional_uses(self):
        sid = "DTXSID9022528"
        response = self.client.get(f"/chemical_functional_use_json/?sid={sid}")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["recordsTotal"], 3)
        self.assertEqual(data["recordsFiltered"], 3)
        self.assertEqual(
            '<span title="composition type">Composition</span>', data["data"][0][0]
        )

        response = self.client.get(f"/chemical_functional_use_json/?sid={sid}&puc=137")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["recordsTotal"], 3)
        self.assertEqual(data["recordsFiltered"], 0)
