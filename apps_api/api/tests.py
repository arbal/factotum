import io
import json
import operator
import base64
from collections import OrderedDict

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import connection, reset_queries
from django.test.utils import override_settings
from drf_yasg.generators import EndpointEnumerator
from rest_framework import status
from setuptools import glob

from apps_api.api import views
from apps_api.api.views import ChemicalPresenceTagViewSet
from apps_api.core.test import TestCase

from dashboard import models
from dashboard.tests.factories import ProductFactory


class TestQueryCount(TestCase):
    """Test that the API list query performance is not dependant on the number
    of data returned.
    """

    @override_settings(DEBUG=True)
    def test_query_count(self):
        for endpoint in EndpointEnumerator().get_api_endpoints():
            reset_queries()
            url = endpoint[0]
            # Only hit list endpoints
            if "{" not in url and "}" not in url:
                result = self.get(url)
                if "results" not in result:
                    continue

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
        if key == "kind":
            return "kind.name"
        return key

    def test_retrieve(self):
        puc = models.PUC.objects.all().order_by("id").first()
        response = self.get("/pucs/%d/" % puc.id)
        del response["url"]
        for key in response:
            source = self.get_source_field(key)
            self.assertEqual(operator.attrgetter(source)(puc), response[key])

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
            self.assertEqual(
                operator.attrgetter(source)(puc), response["results"][0][key]
            )
        # test with chemical filter
        chem_pk = models.DSSToxLookup.objects.get(sid=self.dtxsid).pk
        puc = models.PUC.objects.dtxsid_filter(self.dtxsid).all().first()
        count = models.PUC.objects.dtxsid_filter(self.dtxsid).count()
        response = self.get("/pucs/", {"filter[chemical]": chem_pk})
        self.assertEqual(count, response["meta"]["pagination"]["count"])
        del response["results"][0]["url"]
        for key in response["results"][0]:
            source = self.get_source_field(key)
            self.assertEqual(
                operator.attrgetter(source)(puc), response["results"][0][key]
            )
        # test with sid filter
        puc = models.PUC.objects.dtxsid_filter(self.dtxsid).all().first()
        count = models.PUC.objects.dtxsid_filter(self.dtxsid).count()
        response = self.get("/pucs/", {"filter[sid]": self.dtxsid})
        self.assertEqual(count, response["meta"]["pagination"]["count"])
        del response["results"][0]["url"]
        for key in response["results"][0]:
            source = self.get_source_field(key)
            self.assertEqual(
                operator.attrgetter(source)(puc), response["results"][0][key]
            )


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

    def test_create(self):
        # doc = models.DataDocument.objects.first()
        prod = ProductFactory.build()
        # filename = "dave_or_grant.png"
        image_reader = open(
            "sample_files/images/products/product_image_upload_valid/dave_or_grant.png",
            "rb",
        )
        #
        image = image_reader.read()

        # encode the image as b64 in order to deliver it inside the request's JSON,
        # rather than in the multipart FILE. See this comment:
        # https://github.com/json-api/json-api/issues/246#issuecomment-163569165
        image_b64 = base64.b64encode(image)

        post_data = {
            "data": {
                "attributes": {
                    "name": f"{prod.title}",
                    "upc": f"{prod.upc}",
                    "url": "https://www.turtlewax.com/en-us/",
                    "manufacturer": f"{prod.manufacturer}",
                    "color": f"{prod.color}",
                    "brand": f"{prod.brand_name}",
                    "size": f"{prod.size}",
                    "short_description": f"{prod.short_description}",
                    "long_description": f"{prod.long_description}",
                    "large_image": f"{prod.image}",
                    "image": image_b64,
                },
                "relationships": {
                    "dataDocuments": {"data": [{"type": "dataDocument", "id": 155324}]}
                },
                "type": "product",
            }
        }

        response = self.post(
            "/products", data=post_data, authenticate=True, format="vnd.api+json"
        )
        self.assertTrue(response.status_code, status.HTTP_201_CREATED)
        # Confirm that the new product was successfully linked to the data document
        dd = models.DataDocument.objects.get(pk=155324)
        pd = models.ProductDocument.objects.filter(document=dd).last()
        self.assertTrue(models.ProductDocument.objects.filter(document=dd).exists())
        p = pd.product

        # Open source image and newly created image (read binary)
        sample_file = open(
            "sample_files/images/products/product_image_upload_valid/dave_or_grant.png",
            "rb",
        )

        saved_image = p.image.open(mode="rb")
        # Verify binary data is identical
        self.assertEqual(saved_image.read(), sample_file.read())

    def test_create_duplicate_upc_error(self):
        # doc = models.DataDocument.objects.first()
        prod = ProductFactory.build()
        dupe_upc = models.Product.objects.first().upc
        prod.upc = dupe_upc
        # change the
        # filename = "dave_or_grant.png"
        image_reader = open(
            "sample_files/images/products/product_image_upload_valid/dave_or_grant.png",
            "rb",
        )
        #
        image = image_reader.read()

        # encode the image as b64 in order to deliver it inside the request's JSON,
        # rather than in the multipart FILE. See this comment:
        # https://github.com/json-api/json-api/issues/246#issuecomment-163569165
        image_b64 = base64.b64encode(image)

        post_data = {
            "data": {
                "attributes": {
                    "name": f"{prod.title}",
                    "upc": f"{prod.upc}",
                    "url": "https://www.turtlewax.com/en-us/",
                    "manufacturer": f"{prod.manufacturer}",
                    "color": f"{prod.color}",
                    "brand": f"{prod.brand_name}",
                    "size": f"{prod.size}",
                    "short_description": f"{prod.short_description}",
                    "long_description": f"{prod.long_description}",
                    "large_image": f"{prod.image}",
                    "image": image_b64,
                },
                "relationships": {
                    "dataDocuments": {"data": [{"type": "dataDocument", "id": 155324}]}
                },
                "type": "product",
            }
        }

        response = self.post(
            "/products", data=post_data, authenticate=True, format="vnd.api+json"
        )
        self.assertContains(
            response, "product with this upc already exists", status_code=400
        )

    def test_create_bulk(self):
        doc = models.DataDocument.objects.first()
        pre_product_count = doc.products.count()

        sample_csv = (
            "data_document_id,data_document_filename,title,upc,url,brand_name,size,color,item_id,parent_item_id,short_description,long_description,epa_reg_number,thumb_image,medium_image,large_image,model_number,manufacturer,image_name\n"
            f"{doc.pk},fff53301-a199-4e1b-91b4-39227ca0fe3c.pdf,product title a,110230011425,url,brand_name,size,color,1,1,short_description,long_description,epa_reg_number,thumb_image,medium_image,large_image,model_number,manufacturer\n"
        )

        response = self.post(
            "/products/bulk", self.get_csv(sample_csv), format="multipart"
        )

        self.assertTrue(response.status_code, status.HTTP_202_ACCEPTED)

        # Assert one product was created
        self.assertEqual(doc.products.count(), pre_product_count + 1)

    def test_create_bulk_unauthorized(self):
        response = self.post("/products/bulk", authenticate=False)
        self.assertEqual(response.status_code, 401)

    def test_create_bulk_with_images(self):
        doc = models.DataDocument.objects.first()
        pre_product_count = doc.products.count()

        sample_csv = (
            "data_document_id,data_document_filename,title,upc,url,brand_name,size,color,item_id,parent_item_id,short_description,long_description,epa_reg_number,thumb_image,medium_image,large_image,model_number,manufacturer,image_name\n"
            f"{doc.pk},fff53301-a199-4e1b-91b4-39227ca0fe3c.pdf,product title a,110230011425,url,brand_name,size,color,1,1,short_description,long_description,epa_reg_number,thumb_image,medium_image,large_image,model_number,manufacturer,dave_or_grant.png\n"
        )

        response = self.post(
            "/products/bulk",
            self.get_csv(sample_csv, image_directory_name="product_image_upload_valid"),
            format="multipart",
        )

        # Open source file and newly created file (read binary)
        sample_file = open(
            "sample_files/images/products/product_image_upload_valid/dave_or_grant.png",
            "rb",
        )
        saved_image = (
            models.Product.objects.filter(title="product title a")
            .get()
            .image.open(mode="rb")
        )
        self.assertTrue(response.status_code, status.HTTP_202_ACCEPTED)
        # Assert one product was created
        self.assertEqual(doc.products.count(), pre_product_count + 1)
        # Verify binary data is identical
        self.assertEqual(saved_image.read(), sample_file.read())

    def get_csv(self, sample_csv, image_directory_name=""):
        """
        For DRY purposes, this method takes a csv string
        generated above and returns a POST request that includes it

        :param sample_csv - ProductCSVForm
        :param image_directory_name - str - Name of directory to source images from.
                                            Searches in sample_files/images/products/
        """
        image_directory = []
        if image_directory_name:
            for file in glob.glob(
                f"sample_files/images/products/{image_directory_name}/*"
            ):
                with open(file, "rb") as img:
                    image_bytes = img.read()
                    image_directory.append(
                        InMemoryUploadedFile(
                            io.BytesIO(image_bytes),
                            field_name="products-bulkformsetimagesupload",
                            name=file,
                            content_type="image/png",
                            size=len(image_bytes),
                            charset="utf-8",
                        )
                    )

        sample_csv_bytes = sample_csv.encode(encoding="UTF-8", errors="strict")
        in_mem_sample_csv = InMemoryUploadedFile(
            io.BytesIO(sample_csv_bytes),
            field_name="products-bulkformsetfileupload",
            name="clean_product_data.csv",
            content_type="text/csv",
            size=len(sample_csv),
            charset="utf-8",
        )
        return {
            "csv": in_mem_sample_csv,
            "images": image_directory if image_directory_name else "",
        }


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


class TestChemicalInstance(TestCase):
    qs = models.RawChem.objects.select_subclasses().order_by("id")

    def get_source_field(self, key):
        if key == "lower_weight_fraction":
            return "lower_wf_analysis"
        if key == "central_weight_fraction":
            return "central_wf_analysis"
        if key == "upper_weight_fraction":
            return "upper_wf_analysis"
        if key == "name":
            return "raw_chem_name"
        if key == "cas":
            return "raw_cas"
        return key

    # This test was disabled because retrieve now returns a 400.
    # def test_retrieve(self):
    #     puc_subquery = models.PUC.objects.filter(pk=OuterRef("pk"))
    #     product = (
    #         models.Product.objects.annotate(has_pucs=Exists(puc_subquery))
    #         .filter(has_pucs=True)
    #         .first()
    #     )
    #     chemical = models.DSSToxLookup.objects.first()
    #
    #     chemical_instance_list = [
    #         factories.ExtractedChemicalFactory(),
    #         factories.ExtractedListPresenceFactory(),
    #         factories.ExtractedFunctionalUseFactory(),
    #         factories.ExtractedHHRecFactory(),
    #     ]
    #
    #     for chemical_instance in chemical_instance_list:
    #         chemical_instance.extracted_text.data_document.products.add(product)
    #         chemical_instance.dsstox = chemical
    #         chemical_instance.save()
    #
    #     for chemical_instance in chemical_instance_list:
    #         with self.settings(ROOT_URLCONF="factotum.urls.api"):
    #             response = self.client.get(
    #                 f"/chemicalInstances/{chemical_instance.id}/",
    #                 {"include": "products,chemical,dataDocument,products.puc"},
    #             )
    #         response_data = response.data
    #         del response_data["url"]
    #         for key in response_data:
    #             # Test attributes
    #             if type(response_data[key]) not in [OrderedDict, list]:
    #                 source = self.get_source_field(key)
    #                 value = operator.attrgetter(source)(chemical_instance)
    #                 if type(value) is float:
    #                     value = round(value, 15)
    #                 self.assertEqual(
    #                     str(value),
    #                     str(response_data[key]),
    #                     f"{key} returned incorrect results",
    #                 )
    #             # Test Related Resources are included
    #             elif type(response_data[key]) is list:
    #                 self.assertEqual(response_data[key][0]["type"], "product")
    #             else:
    #                 if response_data[key]["type"] == "chemical":
    #                     self.assertEqual(
    #                         response_data[key]["id"], str(chemical_instance.dsstox.pk)
    #                     )
    #                 elif response_data[key]["type"] == "dataDocument":
    #                     self.assertEqual(
    #                         response_data[key]["id"],
    #                         str(chemical_instance.extracted_text.data_document_id),
    #                     )
    #         # Test Includes - still needed

    def test_retrieve(self):
        pk = models.RawChem.objects.first().pk
        with self.settings(ROOT_URLCONF="factotum.urls.api"):
            resp = self.client.get(f"/chemicalInstances/{pk}/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list(self):
        # test without filter
        count = self.qs.count()
        response = self.get("/chemicalInstances/")
        self.assertTrue("meta" in response)
        self.assertEqual(count, response["meta"]["pagination"]["count"])

        # test with rid.isnull filters
        rid_count = self.qs.exclude(rid="").count()
        blank_rid_count = self.qs.filter(rid="").count()
        response_rid = self.get("/chemicalInstances/", {"filter[rid.isnull]": "false"})
        response_blank_rid = self.get(
            "/chemicalInstances/", {"filter[rid.isnull]": "true"}
        )
        self.assertEqual(rid_count, response_rid["meta"]["pagination"]["count"])
        self.assertEqual(
            blank_rid_count, response_blank_rid["meta"]["pagination"]["count"]
        )

        # test with sid and chemical filters
        curated_chem = self.qs.filter(dsstox__isnull=False).first()
        count = self.qs.filter(dsstox=curated_chem.dsstox).count()
        response_chemical = self.get(
            "/chemicalInstances/", {"filter[chemical]": curated_chem.dsstox.pk}
        )
        response_sid = self.get(
            "/chemicalInstances/", {"filter[sid]": curated_chem.dsstox.sid}
        )
        self.assertEqual(count, response_chemical["meta"]["pagination"]["count"])
        self.assertEqual(count, response_sid["meta"]["pagination"]["count"])

        # test with rid filter
        rc_with_rid = self.qs.filter(rid__isnull=False).first()
        with self.settings(ROOT_URLCONF="factotum.urls.api"):
            response = self.client.get(
                "/chemicalInstances/",
                {
                    "filter[rid]": rc_with_rid.rid,
                    "include": "dataDocument,products,chemical,products.puc",
                },
            )
        # Get included data
        included_data = json.loads(response.content)["included"]
        response = response.data
        self.assertEqual(
            1,
            response["meta"]["pagination"]["count"],
            f"Multiple results returned for Raw Chemicals with rid {rc_with_rid.rid}",
        )

        # Test attributes.  This could be removed if the fetch endpoint is readded.
        #  Using the RID filter because it should return only one result
        row_one_results = response["results"][0]
        del row_one_results["url"]
        for key in row_one_results:
            # Test attributes
            if type(row_one_results[key]) not in [OrderedDict, list]:
                source = self.get_source_field(key)
                value = operator.attrgetter(source)(rc_with_rid)
                if type(value) is float:
                    value = round(value, 15)
                self.assertEqual(
                    str(value),
                    str(row_one_results[key]),
                    f"{key} returned incorrect results",
                )
            # Test Related Resources
            elif type(row_one_results[key]) is list:
                self.assertEqual(row_one_results[key][0]["type"], "product")
            else:
                if row_one_results[key]["type"] == "chemical":
                    if rc_with_rid.dsstox:
                        self.assertEqual(
                            row_one_results[key]["id"], str(rc_with_rid.dsstox.pk)
                        )
                elif row_one_results[key]["type"] == "dataDocument":
                    self.assertEqual(
                        row_one_results[key]["id"],
                        str(rc_with_rid.extracted_text.data_document_id),
                    )
        # Test includes
        self.assertListEqual(
            ["chemical", "dataDocument", "product", "puc"],
            [resource["type"] for resource in included_data],
        )


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
        self.assertEqual(str(doc.data_group.id), response["dataGroup"]["id"])
        self.assertEqual(
            str(doc.data_group.data_source.id), response["dataSource"]["id"]
        )
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


class TestDataSource(TestCase):
    def test_retrieve(self):
        source = models.DataSource.objects.first()
        response = self.get("/dataSources/%d/" % source.id)
        self.assertEqual(response["title"], source.title)
        self.assertEqual(response["source_url"], source.url)
        self.assertEqual(response["description"], source.description)
        self.assertEqual(response["estimated_records"], source.estimated_records)
        self.assertEqual(response["state"], source.state)
        self.assertEqual(response["priority"], source.priority)

    def test_list(self):
        count = models.DataSource.objects.count()
        response = self.get("/dataSources/")
        self.assertTrue("meta" in response)
        self.assertEqual(count, response["meta"]["pagination"]["count"])


class TestDataGroup(TestCase):
    def test_retrieve(self):
        group = models.DataGroup.objects.first()
        response = self.get("/dataGroups/%d/" % group.id)
        self.assertEqual(response["name"], group.name)
        self.assertEqual(response["description"], group.description)
        self.assertEqual(response["group_type"], group.group_type.title)
        self.assertEqual(response["group_type_code"], group.group_type.code)
        self.assertEqual(response["dataSource"]["id"], str(group.data_source.id))

    def test_list(self):
        count = models.DataGroup.objects.count()
        response = self.get("/dataGroups/")
        self.assertTrue("meta" in response)
        self.assertEqual(count, response["meta"]["pagination"]["count"])


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

        response = self.get("/functionalUses/?filter[dataDocument]=%d" % document_id)
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
        response = self.get("/chemicalpresence/?data_document=%s" % document_id)
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
        response_doc_filter = self.get(f"/compositions/?filter[dataDocument]={doc_id}")
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
        self.assertEqual(
            composition.weight_fraction_type.title,
            response_rid_filter["results"][0]["weight_fraction_type"],
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
