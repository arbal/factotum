import uuid

from django.db import connection, reset_queries
from django.test.utils import override_settings
from drf_yasg.generators import EndpointEnumerator

from apps_api.api import views
from apps_api.api.serializers import ExtractedChemicalSerializer
from apps_api.api.views import ChemicalPresenceTagViewSet
from apps_api.core.test import TestCase

from dashboard import models
from unittest import skip


class TestQueryCount(TestCase):
    """Test that the API list query performance is not dependant on the number
    of data returned.
    """

    @override_settings(DEBUG=True)
    def test_query_count(self):
        reset_queries()
        for endpoint in EndpointEnumerator().get_api_endpoints():
            url = endpoint[0]
            if url == "/token/" or url == "/chemicalpresence/":
                continue
            # Only hit list endpoints
            if "{" not in url and "}" not in url:
                result = self.get(url)
                max_queries = len(result["results"])
                num_queries = len(connection.queries)
                # Number of queries must be less than the number of data objects returned.
                self.assertTrue(
                    num_queries < max_queries,
                    f"Endpoint '{url}' made {num_queries} SQL queries. The maximum allowed query count is {max_queries}. Adjust the view's queryset to use 'select_related' or 'prefetch_related'.",
                )
                reset_queries()


class TestMetrics(TestCase):
    def tet_metrics_endpoint(self):
        response = self.get("/metrics")
        self.assertEqual(response.status_code, 200)


class TestPUC(TestCase):
    dtxsid = "DTXSID6026296"

    def get_source_field(self, key):
        if key == "level_1_category":
            return "gen_cat"
        if key == "level_2_category":
            return "prod_fam"
        if key == "level_3_category":
            return "prod_type"
        if key == "definition":
            return "description"
        return key

    def test_retrieve(self):
        puc = models.PUC.objects.all().order_by("id").first()
        response = self.get("/pucs/%d/" % puc.id)
        del response["url"]
        for key in response:
            source = self.get_source_field(key)
            self.assertEqual(getattr(puc, source), response[key])

    def test_list(self):
        puc = models.PUC.objects.all().order_by("id").first()
        count = models.PUC.objects.all().count()
        # test without filter
        response = self.get("/pucs/")
        self.assertTrue("meta" in response)
        self.assertEqual(count, response["meta"]["pagination"]["count"])
        del response["results"][0]["url"]
        for key in response["results"][0]:
            source = self.get_source_field(key)
            self.assertEqual(getattr(puc, source), response["results"][0][key])
        # test with filter
        puc = models.PUC.objects.dtxsid_filter(self.dtxsid).all().first()
        count = models.PUC.objects.dtxsid_filter(self.dtxsid).count()
        response = self.get("/pucs/", {"filter[chemical]": self.dtxsid})
        self.assertEqual(count, response["meta"]["pagination"]["count"])
        del response["results"][0]["url"]
        for key in response["results"][0]:
            source = self.get_source_field(key)
            self.assertEqual(getattr(puc, source), response["results"][0][key])


class TestProduct(TestCase):
    chem_id = 8
    dtxsid = "DTXSID6026296"
    upc = "stub_1872"

    def test_retrieve(self):
        product = models.Product.objects.get(id=1867)
        response = self.get("/products/%d/" % product.id)
        for key in (
            "id",
            "name",
            "upc",
            "manufacturer",
            "brand",
            "puc",
            "dataDocuments",
        ):
            self.assertTrue(key in response)
        self.assertEqual(response["id"], product.id)
        self.assertEqual(response["name"], product.title)
        self.assertEqual(response["upc"], product.upc)
        self.assertEqual(response["dataDocuments"][0]["id"], "130169")
        self.assertEqual(response["puc"]["id"], str(product.uber_puc.id))

    def test_page_size(self):
        response = self.get("/products/?page[size]=35")
        self.assertEqual(35, len(response["results"]))

    def test_list(self):
        # test without filter
        count = models.Product.objects.count()
        response = self.get("/products/")
        self.assertTrue("meta" in response)
        self.assertEqual(count, response["meta"]["pagination"]["count"])
        # test with sid filter
        count = models.Product.objects.filter(
            datadocument__extractedtext__rawchem__dsstox__sid=self.dtxsid
        ).count()
        response = self.get("/products/", {"filter[sid]": self.dtxsid})
        self.assertEqual(count, response["meta"]["pagination"]["count"])
        # test with chemical id filter
        response = self.get("/products/", {"filter[chemical]": self.chem_id})
        self.assertEqual(count, response["meta"]["pagination"]["count"])
        # test with UPC filter
        count = models.Product.objects.filter(upc=self.upc).count()
        response = self.get("/products/", {"filter[upc]": self.upc})
        self.assertEqual(count, response["meta"]["pagination"]["count"])
        self.assertEqual(self.upc, response["results"][0]["upc"])


class TestChemical(TestCase):
    qs = models.DSSToxLookup.objects.exclude(curated_chemical__isnull=True)

    def test_retrieve(self):
        chem = self.qs.first()
        response = self.get(f"/chemicals/{chem.id}/")
        self.assertEqual(response["sid"], chem.sid)
        self.assertEqual(response["name"], chem.true_chemname)
        self.assertEqual(response["cas"], chem.true_cas)

    def test_list(self):
        # test without filter
        count = self.qs.count()
        response = self.get("/chemicals/")
        self.assertTrue("meta" in response)
        self.assertEqual(count, response["meta"]["pagination"]["count"])

        # test with PUC filter
        count = self.qs.filter(
            curated_chemical__extracted_text__data_document__product__puc__id=1
        ).count()
        response = self.get("/chemicals/", {"filter[puc]": 1})
        self.assertEqual(count, response["meta"]["pagination"]["count"])


class TestChemicalPresence(TestCase):
    qs = models.ExtractedListPresenceTag.objects.all()

    def test_retrieve(self):
        tag = self.qs.first()
        response = self.get("/chemicalpresences/%s/" % tag.id)
        self.assertEqual(response["name"], tag.name)
        self.assertEqual(response["definition"], tag.definition)
        self.assertEqual(response["kind"], tag.kind.name)

    def test_list(self):
        count = self.qs.count()
        response = self.get("/chemicalpresences/")
        self.assertTrue("meta" in response)
        self.assertEqual(count, response["meta"]["pagination"]["count"])


class TestDocument(TestCase):
    def test_retrieve(self):
        doc_id = 147446
        doc = models.DataDocument.objects.prefetch_related("products").get(id=doc_id)
        response = self.get("/dataDocuments/%d/" % doc.id)

        self.assertEqual(doc.title, response["title"])
        self.assertEqual(doc.subtitle, response["subtitle"])
        self.assertEqual(doc.organization, response["organization"])
        self.assertEqual(doc.extractedtext.doc_date, response["date"])
        self.assertEqual(doc.data_group.group_type.title, response["data_type"])
        self.assertEqual(doc.document_type.title, response["document_type"])
        self.assertEqual(doc.file.url, response["document_url"])
        self.assertEqual(doc.note, response["notes"])
        self.assertEqual(
            doc.chemicals.filter(dsstox__isnull=False).count(),
            len(response["chemicals"]),
        )

    def test_list(self):
        # test without filter
        response = self.get("/dataDocuments/")
        self.assertTrue("meta" in response)
        count = models.DataDocument.objects.count()
        self.assertEqual(count, response["meta"]["pagination"]["count"])


@skip("This serializer will be replaced")
class TestExtractedChemicalSerializer(TestCase):
    def test_serialize(self):
        et = models.ExtractedText.objects.first()
        dsstox = models.DSSToxLookup.objects.first()
        extracted_chemical = models.ExtractedChemical.objects.create(
            extracted_text=et,
            component=str(uuid.uuid1()),
            lower_wf_analysis=0.1,
            central_wf_analysis=0.2,
            upper_wf_analysis=0.3,
            ingredient_rank=1,
        )
        extracted_chemical.dsstox = dsstox
        serialized_extracted_chemical = ExtractedChemicalSerializer(extracted_chemical)

        self.assertEqual(
            extracted_chemical.component,
            serialized_extracted_chemical.data["component"],
        )
        self.assertEqual(
            format(extracted_chemical.lower_wf_analysis, ".15f"),
            serialized_extracted_chemical.data["lower_weight_fraction"],
        )
        self.assertEqual(
            format(extracted_chemical.central_wf_analysis, ".15f"),
            serialized_extracted_chemical.data["central_weight_fraction"],
        )
        self.assertEqual(
            format(extracted_chemical.upper_wf_analysis, ".15f"),
            serialized_extracted_chemical.data["upper_weight_fraction"],
        )
        self.assertEqual(
            extracted_chemical.ingredient_rank,
            serialized_extracted_chemical.data["ingredient_rank"],
        )


class TestFunctionalUse(TestCase):
    # disabled the invalid without filter assertion.
    # def test_no_filter_error(self):
    #     response = self.get("/function/")
    #     self.assertEqual("invalid", response[0].code)

    def test_document_filter(self):
        document_id = 156051
        dataset = models.FunctionalUse.objects.filter(
            chem__extracted_text__data_document_id=document_id
        ).order_by("id")
        count = dataset.count()
        func_use = dataset.first()

        response = self.get("/functionalUses/?filter[document]=%d" % document_id)
        self.assertTrue("meta" in response)
        self.assertEqual(count, response["meta"]["pagination"]["count"])
        data = response["results"][0]
        self.assertIsNotNone(data)
        self.assertEquals(
            str(func_use.chem.extracted_text.data_document_id),
            data["dataDocument"]["id"],
        )
        self.assertEquals(str(func_use.chem.dsstox.id), data["chemical"]["id"])
        self.assertEquals(func_use.chem.rid, data["rid"])

    def test_chemical_filter(self):
        chemical_id = "DTXSID9022528"
        dataset = models.FunctionalUse.objects.filter(
            chem__dsstox__sid=chemical_id
        ).order_by("id")
        count = dataset.count()
        func_use = dataset.first()

        response = self.get("/functionalUses/?filter[chemical]=%s" % chemical_id)
        self.assertTrue("meta" in response)
        self.assertEqual(count, response["meta"]["pagination"]["count"])
        data = response["results"][0]
        self.assertIsNotNone(data)
        self.assertEquals(
            str(func_use.chem.extracted_text.data_document_id),
            data["dataDocument"]["id"],
        )
        self.assertEquals(str(func_use.chem.dsstox.id), data["chemical"]["id"])
        self.assertEquals(func_use.chem.rid, data["rid"])

    def test_category_filter(self):
        category_id = 1
        dataset = models.FunctionalUse.objects.filter(category=category_id).order_by(
            "id"
        )
        count = dataset.count()
        func_use = dataset.first()

        response = self.get("/functionalUses/?filter[category]=%d" % category_id)
        self.assertTrue("meta" in response)
        self.assertEqual(count, response["meta"]["pagination"]["count"])
        data = response["results"][0]
        self.assertIsNotNone(data)
        self.assertEquals(
            str(func_use.chem.extracted_text.data_document_id),
            data["dataDocument"]["id"],
        )
        self.assertEquals(str(func_use.chem.dsstox.id), data["chemical"]["id"])
        self.assertEquals(func_use.chem.rid, data["rid"])


class TestFunctionalUseCategory(TestCase):
    def test_retrieve(self):
        fu_cat = models.FunctionalUseCategory.objects.first()
        response = self.get("/functionalUseCategories/%d/" % fu_cat.id)
        self.assertEqual(response["title"], fu_cat.title)
        self.assertEqual(response["description"], fu_cat.description)

    def test_list(self):
        count = models.FunctionalUseCategory.objects.count()
        response = self.get("/functionalUseCategories/")
        self.assertTrue("meta" in response)
        self.assertEqual(count, response["meta"]["pagination"]["count"])


class TestChemicalPresenceTags(TestCase):
    queryset = ChemicalPresenceTagViewSet.queryset

    def test_no_filter_error(self):
        response = self.get("/chemicalpresence/")
        self.assertEqual("invalid", response[0].code)

    def test_chemical_filter(self):
        chemical_id = "DTXSID9020584"
        dataset = self.queryset.filter(sid=chemical_id).distinct()
        count = dataset.count()
        first_chemical = dataset.first()
        tagsets = first_chemical.get_tags_with_extracted_text()
        response = self.get("/chemicalpresence/?chemical=%s" % chemical_id)
        data = response["results"][0]

        self.assertTrue("meta" in response)
        self.assertEqual(count, response["meta"]["pagination"]["count"])
        self.assertIsNotNone(data)
        self.assertEquals(first_chemical.sid, data["chemical_id"])
        for keyword in data["keyword_sets"][0]["keywords"]:
            self.assertIn(keyword["name"], [tag.name for tag in tagsets[0]["tags"]])
        self.assertEqual(
            int(data["keyword_sets"][0]["related"][0]["document_id"]),
            tagsets[0]["related"][0]["extracted_text"].data_document_id,
        )
        self.assertListEqual(
            data["keyword_sets"][0]["related"][0]["rids"],
            [elp.rid for elp in tagsets[0]["related"][0]["extracted_list_presence"]],
        )

    def test_tag_filter(self):
        tag_id = 1
        dataset = self.queryset.filter(
            curated_chemical__extractedlistpresence__tags__pk=tag_id
        ).distinct()
        count = dataset.count()
        first_chemical = dataset.first()
        tagsets = first_chemical.get_tags_with_extracted_text(tag_id=tag_id)
        response = self.get("/chemicalpresence/?keyword=%s" % tag_id)
        data = response["results"][0]

        self.assertTrue("meta" in response)
        self.assertEqual(count, response["meta"]["pagination"]["count"])
        self.assertIsNotNone(data)
        self.assertEquals(first_chemical.sid, data["chemical_id"])
        for keyword in data["keyword_sets"][0]["keywords"]:
            self.assertIn(keyword["name"], [tag.name for tag in tagsets[0]["tags"]])
        self.assertEqual(
            int(data["keyword_sets"][0]["related"][0]["document_id"]),
            tagsets[0]["related"][0]["extracted_text"].data_document_id,
        )
        self.assertListEqual(
            data["keyword_sets"][0]["related"][0]["rids"],
            [elp.rid for elp in tagsets[0]["related"][0]["extracted_list_presence"]],
        )

    def test_document_filter(self):
        document_id = 254781
        dataset = self.queryset.filter(
            curated_chemical__extracted_text__data_document_id=document_id
        ).distinct()
        count = dataset.count()
        first_chemical = dataset.first()
        tagsets = first_chemical.get_tags_with_extracted_text(doc_id=document_id)
        response = self.get("/chemicalpresence/?document=%s" % document_id)
        data = response["results"][0]

        self.assertTrue("meta" in response)
        self.assertEqual(count, response["meta"]["pagination"]["count"])
        self.assertIsNotNone(data)
        self.assertEquals(first_chemical.sid, data["chemical_id"])
        for keyword in data["keyword_sets"][0]["keywords"]:
            self.assertIn(keyword["name"], [tag.name for tag in tagsets[0]["tags"]])
        self.assertEqual(
            int(data["keyword_sets"][0]["related"][0]["document_id"]),
            tagsets[0]["related"][0]["extracted_text"].data_document_id,
        )
        self.assertListEqual(
            data["keyword_sets"][0]["related"][0]["rids"],
            [elp.rid for elp in tagsets[0]["related"][0]["extracted_list_presence"]],
        )


class TestComposition(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.queryset = views.CompositionViewSet.queryset

    def test_filter(self):
        doc_id = 156051
        chem_id = 12
        chem_sid = "DTXSID9022528"
        rid = "DTXRID002"
        prod_id = 1868

        response_rid_filter = self.get(f"/compositions/?filter[rid]={rid}")
        response_doc_filter = self.get(f"/compositions/?filter[document]={doc_id}")
        response_chem_filter = self.get(f"/compositions/?filter[chemical]={chem_id}")
        response_sid_filter = self.get(f"/compositions/?filter[sid]={chem_sid}")
        response_prod_filter = self.get(f"/compositions/?filter[product]={prod_id}")

        composition = self.queryset.get(rid=rid)

        self.assertTrue("meta" in response_rid_filter)
        self.assertEqual(
            self.queryset.filter(rid=rid).count(),
            response_rid_filter["meta"]["pagination"]["count"],
        )
        self.assertEqual(composition.rid, response_rid_filter["results"][0]["rid"])
        self.assertEqual(
            composition.ingredient_rank,
            response_rid_filter["results"][0]["ingredient_rank"],
        )
        self.assertAlmostEqual(
            composition.lower_wf_analysis,
            self._cast_to_float(
                response_rid_filter["results"][0]["lower_weight_fraction"]
            ),
        )
        self.assertAlmostEqual(
            composition.central_wf_analysis,
            self._cast_to_float(
                response_rid_filter["results"][0]["central_weight_fraction"]
            ),
        )
        self.assertAlmostEqual(
            composition.upper_wf_analysis,
            self._cast_to_float(
                response_rid_filter["results"][0]["upper_weight_fraction"]
            ),
        )
        self.assertEqual(
            composition.component, response_rid_filter["results"][0]["component"]
        )
        self.assertEqual(
            str(composition.extracted_text.data_document_id),
            response_rid_filter["results"][0]["dataDocument"]["id"],
        )
        self.assertEqual(
            composition.extracted_text.data_document.products.count(),
            len(response_rid_filter["results"][0]["products"]),
        )
        self.assertEqual(
            self.queryset.filter(extracted_text__data_document_id=doc_id).count(),
            response_doc_filter["meta"]["pagination"]["count"],
        )
        self.assertEqual(
            self.queryset.filter(dsstox__id=chem_id).count(),
            response_chem_filter["meta"]["pagination"]["count"],
        )
        self.assertEqual(
            self.queryset.filter(dsstox__sid=chem_sid).count(),
            response_sid_filter["meta"]["pagination"]["count"],
        )
        self.assertEqual(
            self.queryset.filter(
                extracted_text__data_document__products__pk=prod_id
            ).count(),
            response_prod_filter["meta"]["pagination"]["count"],
        )

    def _cast_to_float(self, value):
        """Attempts to cast a value to float returns the object on failure
        """
        try:
            return float(value)
        except TypeError:
            return value
