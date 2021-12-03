import io
import re
from datetime import datetime
import glob

from django.test import RequestFactory, TestCase, Client, tag
from django.contrib.auth.models import User
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils.timezone import now

from dashboard import views
from dashboard.models import (
    Product,
    DuplicateProduct,
    DataDocument,
    ProductDocument,
    DataSource,
    DataGroup,
    GroupType,
)
from dashboard.tests.loader import fixtures_standard
from dashboard.tests.mixins import TempFileMixin
from factotum.environment import env


class UploadProductTest(TempFileMixin, TestCase):
    # fixtures = fixtures_standard

    def setUp(self):
        self.c = Client()
        self.factory = RequestFactory()
        self.c.login(username="Karyn", password="specialP@55word")

    @classmethod
    def setUpTestData(cls):
        user = User.objects.create_user(username="Karyn", password="specialP@55word")
        ds = DataSource.objects.create(title="Test Data Source")
        group_type = GroupType.objects.create(code="CO", title="Composition")
        cls.dg = DataGroup.objects.create(
            group_type=group_type,
            downloaded_at=now(),
            downloaded_by=user,
            data_source=ds,
        )
        cls.docs = []
        for i in range(5):
            cls.docs.append(DataDocument.objects.create(data_group=cls.dg))

    def post_csv(self, sample_csv, image_directory_name=""):
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
        data = {
            "products-submit": "Submit",
            "products-TOTAL_FORMS": 0,
            "products-INITIAL_FORMS": 0,
            "products-MAX_NUM_FORMS": "",
            "products-bulkformsetfileupload": in_mem_sample_csv,
            "products-bulkformsetimageupload": image_directory
            if image_directory_name
            else "",
        }
        return self.c.post(path=f"/datagroup/{self.dg.pk}/", data=data, follow=True)

    def test_valid_product_data_upload(self):
        sample_csv = (
            "data_document_id,data_document_filename,title,upc,url,brand_name,size,color,item_id,parent_item_id,short_description,long_description,epa_reg_number,thumb_image,medium_image,large_image,model_number,manufacturer,image_name\n"
            f"{self.docs[0].pk},fff53301-a199-4e1b-91b4-39227ca0fe3c.pdf,product title a,110230011425,url,brand_name,size,color,1,1,short_description,long_description,epa_reg_number,thumb_image,medium_image,large_image,model_number,manufacturer\n"
            f"{self.docs[1].pk},fefd813f-d1e0-4fa7-8c4e-49030eca08a3.pdf,'product title b',903944840750\n"
            f"{self.docs[2].pk},fc5f964c-91e2-42c5-9899-2ff38e37ba89.pdf,'product title c',852646877466\n"
            f"{self.docs[3].pk},f040f93d-1cf3-4eff-85a9-da14d8d2e252.pdf,'product title d'\n"
            f"{self.docs[4].pk},f040f93d-1cf3-4eff-85a9-da14d8d2e253.pdf,'product title e'"
        )
        pre_pdcount = ProductDocument.objects.count()
        resp = self.post_csv(sample_csv)
        self.assertContains(resp, "5 records have been successfully uploaded.")
        # ProductDocument records should also have been added
        post_pdcount = ProductDocument.objects.count()
        self.assertEqual(
            post_pdcount,
            pre_pdcount + 5,
            "There should be 5 more ProductDocuments after the upload",
        )
        # The first data_document_id in the csv should now have
        # two Products linked to it, including the new one
        resp = self.c.get(f"/datadocument/%s/" % self.docs[0].pk)
        self.assertContains(resp, "product title a")

        # Test rows from newly created product have been set on the resulting product model.
        product_a = Product.objects.get(title="product title a", upc="110230011425")
        excluded_product_fields = ["source_category", "image"]
        for field in product_a._meta.fields:
            if field.name not in excluded_product_fields:
                self.assertTrue(
                    getattr(product_a, field.name),
                    f"Product field {field.name} is not being set by csv",
                )

    @tag("fails_in_suite")
    def test_valid_product_data_upload_with_image(self):
        sample_csv = (
            "data_document_id,data_document_filename,title,upc,url,brand_name,size,color,item_id,parent_item_id,short_description,long_description,epa_reg_number,thumb_image,medium_image,large_image,model_number,manufacturer,image_name\n"
            f"{self.docs[0].pk},fff53301-a199-4e1b-91b4-39227ca0fe3c.pdf,product title a,110230011425,,,,,,,,,,,,,,,dave_or_grant.png\n"
            f"{self.docs[1].pk},fefd813f-d1e0-4fa7-8c4e-49030eca08a3.pdf,product title b,903944840750\n"
            f"{self.docs[2].pk},fc5f964c-91e2-42c5-9899-2ff38e37ba89.pdf,product title c,852646877466\n"
            f"{self.docs[3].pk},f040f93d-1cf3-4eff-85a9-da14d8d2e252.pdf,product title d\n"
            f"{self.docs[4].pk},f040f93d-1cf3-4eff-85a9-da14d8d2e253.pdf,product title e"
        )
        pre_pdcount = ProductDocument.objects.count()
        resp = self.post_csv(
            sample_csv, image_directory_name="product_image_upload_valid"
        )
        self.assertContains(resp, "5 records have been successfully uploaded.")
        # ProductDocument records should also have been added
        post_pdcount = ProductDocument.objects.count()
        self.assertEqual(
            post_pdcount,
            pre_pdcount + 5,
            "There should be 5 more ProductDocuments after the upload",
        )

        sample_file = open(
            "sample_files/images/products/product_image_upload_valid/dave_or_grant.png",
            "rb",
        )
        saved_image = (
            Product.objects.filter(title="product title a").get().image.open(mode="rb")
        )
        # Verify binary data is identical
        self.assertEqual(saved_image.read(), sample_file.read())

        # The first data_document_id in the csv should now have
        # two Products linked to it, including the new one
        resp = self.c.get(f"/datadocument/%s/" % self.docs[0].pk)
        self.assertContains(resp, "product title a")

        # The product image should appear on its page
        p_id = Product.objects.filter(title="product title a").first().id
        resp = self.c.get(f"/product/%s/" % p_id)
        self.assertContains(resp, "Product Image Url")

    def test_product_data_upload_with_wrong_image_name_single(self):
        """
        A single row with images that arent in the uploaded directory should be rejected
        The document should not be processed
        """
        sample_csv = (
            "data_document_id,data_document_filename,title,upc,url,brand_name,size,color,item_id,parent_item_id,short_description,long_description,epa_reg_number,thumb_image,medium_image,large_image,model_number,manufacturer,image_name\n"
            f"{self.docs[0].pk},fff53301-a199-4e1b-91b4-39227ca0fe3c.pdf,product title a,110230011425,,,,,,,,,,,,,,,dave_or_lincoln.png\n"
            f"{self.docs[1].pk},fff53301-a199-4e1b-91b4-39227ca0fe3c.pdf,product title a,110230011425,,,,,,,,,,,,,,,dave_or_grant.png\n"
        )
        pre_pdcount = ProductDocument.objects.count()
        resp = self.post_csv(
            sample_csv, image_directory_name="product_image_upload_valid"
        )
        post_pdcount = ProductDocument.objects.count()
        self.assertContains(
            resp,
            "The following record images could not be matched.  "
            f"Please correct or remove their image_names and retry the upload: {self.docs[0].pk}",
        )
        self.assertEqual(
            post_pdcount, pre_pdcount, "No rows should have been processed"
        )

    def test_product_data_upload_with_wrong_image_name_multiple(self):
        """
        Rows with images that arent in the uploaded directory should be rejected
        """
        sample_csv = (
            "data_document_id,data_document_filename,title,upc,url,brand_name,size,color,item_id,parent_item_id,short_description,long_description,epa_reg_number,thumb_image,medium_image,large_image,model_number,manufacturer,image_name\n"
            f"{self.docs[0].pk},fff53301-a199-4e1b-91b4-39227ca0fe3c.pdf,product title a,110230011425,,,,,,,,,,,,,,,dave_or_lincoln.png\n"
            f"{self.docs[1].pk},fefd813f-d1e0-4fa7-8c4e-49030eca08a3.pdf,product title b,903944840750,,,,,,,,,,,,,,,foobar.png\n"
        )
        resp = self.post_csv(
            sample_csv, image_directory_name="product_image_upload_valid"
        )
        self.assertContains(
            resp,
            "The following record images could not be matched.  "
            f"Please correct or remove their image_names and retry the upload: {self.docs[0].pk}, {self.docs[1].pk}",
        )

    @tag("fails_in_suite")
    def test_image_file_too_large_error(self):
        """
        Rows with images that arent in the uploaded directory should be rejected
        """
        sample_csv = (
            "data_document_id,data_document_filename,title,upc,url,brand_name,size,color,item_id,parent_item_id,short_description,long_description,epa_reg_number,thumb_image,medium_image,large_image,model_number,manufacturer,image_name\n"
            f"{self.docs[0].pk},fff53301-a199-4e1b-91b4-39227ca0fe3c.pdf,product title a,110230011425,,,,,,,,,,,,,,,dave_or_grant.png\n"
        )
        pre_pdcount = ProductDocument.objects.count()
        resp = self.post_csv(
            sample_csv, image_directory_name="product_image_upload_image_too_large"
        )
        post_pdcount = ProductDocument.objects.count()

        error_message_regex = re.compile(
            "[\s\S]*The following images are too large\.  "
            + "Please reduce their sizes to &lt; 1 MB: "
            + "Ulysses_S_Grant_by_Brady_c1870-restored_large( \(copy\))?\.jpg, "
            + "Ulysses_S_Grant_by_Brady_c1870-restored_large( \(copy\))?\.jpg[\s\S]*"
        )

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(
            error_message_regex.search(resp.content.decode("utf8")),
            "The error message could not be found in the text",
        )
        self.assertEqual(
            post_pdcount, pre_pdcount, "No rows should have been processed"
        )

    @tag("fails_in_suite")
    def test_image_directory_too_large_error(self):
        """
        Rows with images that arent in the uploaded directory should be rejected
        """
        sample_csv = (
            "data_document_id,data_document_filename,title,upc,url,brand_name,size,color,item_id,parent_item_id,short_description,long_description,epa_reg_number,thumb_image,medium_image,large_image,model_number,manufacturer,image_name\n"
            f"{self.docs[0].pk},fff53301-a199-4e1b-91b4-39227ca0fe3c.pdf,product title a,110230011425,,,,,,,,,,,,,,,dave_or_grant.png\n"
        )
        pre_pdcount = ProductDocument.objects.count()
        resp = self.post_csv(
            sample_csv, image_directory_name="product_image_upload_directory_too_large"
        )
        post_pdcount = ProductDocument.objects.count()
        self.assertContains(
            resp,
            "The image directory is too large.  "
            "Please reduce the size of the directory to &lt; %d MB"
            % (env.PRODUCT_IMAGE_DIRECTORY_MAX_UPLOAD / 1000000),
        )
        self.assertEqual(
            post_pdcount, pre_pdcount, "No rows should have been processed"
        )

    @tag("fails_in_suite")
    def test_image_directory_exceeds_count_error(self):
        """
        Rows with images that arent in the uploaded directory should be rejected
        """
        sample_csv = (
            "data_document_id,data_document_filename,title,upc,url,brand_name,size,color,item_id,parent_item_id,short_description,long_description,epa_reg_number,thumb_image,medium_image,large_image,model_number,manufacturer,image_name\n"
            f"{self.docs[0].pk},fff53301-a199-4e1b-91b4-39227ca0fe3c.pdf,product title a,110230011425,,,,,,,,,,,,,,,dave_or_grant.png\n"
        )
        pre_pdcount = ProductDocument.objects.count()
        resp = self.post_csv(
            sample_csv, image_directory_name="product_image_upload_over_max_upload"
        )
        post_pdcount = ProductDocument.objects.count()
        self.assertContains(
            resp,
            "The image directory has too many files.  "
            "Please reduce the number of document upload at one time to &lt; %d."
            % env.PRODUCT_IMAGE_DIRECTORY_MAX_FILE_COUNT,
        )
        self.assertEqual(
            post_pdcount, pre_pdcount, "No rows should have been processed"
        )

    def test_existing_upc_upload(self):
        """
        If a product's UPC already exists in the database, the incoming Product record should be diverted
        to the DuplicateProduct model 
        """
        self.assertEqual(DuplicateProduct.objects.filter(upc="stub_11").count(), 0)
        Product.objects.create(upc="stub_11")
        sample_csv = (
            "data_document_id,data_document_filename,title,upc,url,brand_name,size,color,item_id,parent_item_id,short_description,long_description,epa_reg_number,thumb_image,medium_image,large_image,model_number,manufacturer,image_name\n"
            f"{self.docs[0].pk},fff53301-a199-4e1b-91b4-39227ca0fe3c.pdf,'product title a',110230011425\n"
            f"{self.docs[1].pk},fefd813f-d1e0-4fa7-8c4e-49030eca08a3.pdf,'product title b',903944840750\n"
            f"{self.docs[2].pk},fc5f964c-91e2-42c5-9899-2ff38e37ba89.pdf,'product title c',852646877466\n"
            f"{self.docs[3].pk},f040f93d-1cf3-4eff-85a9-da14d8d2e252.pdf,'product title d',stub_11"
        )
        resp = self.post_csv(sample_csv)
        self.assertContains(
            resp,
            f"The following data documents had existing or duplicated UPCs and their new products were added as duplicates: {self.docs[3].pk}",
        )
        self.assertContains(resp, "3 records have been successfully uploaded")
        self.assertEqual(
            DuplicateProduct.objects.filter(source_upc="stub_11").count(), 1
        )

    def test_duplicate_upc_upload(self):
        """
        The duplicated UPCs in the file should result in both new rows
        being rejected
        """
        sample_csv = (
            "data_document_id,data_document_filename,title,upc,url,brand_name,size,color,item_id,parent_item_id,short_description,long_description,epa_reg_number,thumb_image,medium_image,large_image,model_number,manufacturer,image_name\n"
            f"{self.docs[0].pk},fff53301-a199-4e1b-91b4-39227ca0fe3c.pdf,'product title a',110230011425\n"
            f"{self.docs[1].pk},fefd813f-d1e0-4fa7-8c4e-49030eca08a3.pdf,'product title b',903944840750\n"
            f"{self.docs[2].pk},fc5f964c-91e2-42c5-9899-2ff38e37ba89.pdf,'product title c',852646877466\n"
            f"{self.docs[3].pk},f040f93d-1cf3-4eff-85a9-da14d8d2e252.pdf,'product title d'\n"
            f"{self.docs[4].pk},f040f93d-1cf3-4eff-85a9-da14d8d2e253.pdf,'product title e',852646877466"
        )
        resp = self.post_csv(sample_csv)
        self.assertContains(
            resp,
            f"The following data documents had existing or duplicated UPCs and their new products were added as duplicates: {self.docs[2].pk}, {self.docs[4].pk}",
        )
        self.assertContains(resp, "3 records have been successfully uploaded.")

    def test_bad_header_upload(self):
        """
        The bad header should cause the entire form to be invalid
        """
        sample_csv = (
            "data_document_idX,data_document_file_name,title,upc,url,brand_name,size,color,item_id,parent_item_id,short_description,long_description,epa_reg_number,thumb_image,medium_image,large_image,model_number,manufacturer,image_name\n"
            f"{self.docs[0].pk},fff53301-a199-4e1b-91b4-39227ca0fe3c.pdf,'product title a',110230011425\n"
            f"{self.docs[1].pk},fefd813f-d1e0-4fa7-8c4e-49030eca08a3.pdf,'product title b',903944840750\n"
            f"{self.docs[2].pk},fc5f964c-91e2-42c5-9899-2ff38e37ba89.pdf,'product title c',852646877466\n"
            f"{self.docs[3].pk},f040f93d-1cf3-4eff-85a9-da14d8d2e252.pdf,'product title d'\n"
            f"{self.docs[4].pk},f040f93d-1cf3-4eff-85a9-da14d8d2e253.pdf,'product title e'"
        )
        resp = self.post_csv(sample_csv)
        self.assertContains(resp, "data_document_filename: This field is required.")
        self.assertContains(resp, "CSV column titles should be ")

    def test_blank_upc_upload(self):
        """
        Each UPC should be made and be unique
        """
        sample_csv = (
            "data_document_id,data_document_filename,title,upc,url,brand_name,size,color,item_id,parent_item_id,short_description,long_description,epa_reg_number,thumb_image,medium_image,large_image,model_number,manufacturer,image_name\n"
            f"{self.docs[0].pk},fff53301-a199-4e1b-91b4-39227ca0fe3c.pdf,product without upc a\n"
            f"{self.docs[1].pk},fefd813f-d1e0-4fa7-8c4e-49030eca08a3.pdf,product without upc b\n"
            f"{self.docs[2].pk},fc5f964c-91e2-42c5-9899-2ff38e37ba89.pdf,product without upc c\n"
            f"{self.docs[3].pk},f040f93d-1cf3-4eff-85a9-da14d8d2e252.pdf,product without upc d\n"
            f"{self.docs[4].pk},f040f93d-1cf3-4eff-85a9-da14d8d2e253.pdf,product without upc e"
        )
        pre_pdcount = ProductDocument.objects.count()
        resp = self.post_csv(sample_csv)
        self.assertContains(resp, "5 records have been successfully uploaded.")
        # ProductDocument records should also have been added
        post_pdcount = ProductDocument.objects.count()
        self.assertEqual(
            post_pdcount,
            pre_pdcount + 5,
            "There should be 5 more ProductDocuments after the upload",
        )
        # The first data_document_id in the csv should now have
        # two Products linked to it, including the new one
        resp = self.c.get(f"/datadocument/%s/" % self.docs[0].pk)
        self.assertContains(resp, "product without upc a")

        products = Product.objects.filter(title__startswith="product without upc")
        for product in products:
            self.assertEqual(
                product.upc, "stub_" + str(product.id), "should generated a stub upc"
            )
