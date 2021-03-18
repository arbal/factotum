import os
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.test import TransactionTestCase, TestCase, override_settings
from django.urls import reverse
from lxml import html

from dashboard.forms import create_detail_formset
from dashboard.models import (
    ExtractedText,
    ExtractedCPCat,
    ExtractedHHDoc,
    ExtractedHHRec,
    ExtractedComposition,
    ExtractedHabitsAndPracticesToTag,
    ExtractedListPresence,
    ExtractedListPresenceToTag,
    ExtractedListPresenceTag,
    DataDocument,
    Product,
    RawChem,
)
from dashboard.tests.loader import fixtures_standard, datadocument_models
from dashboard.utils import get_extracted_models


@override_settings(ALLOWED_HOSTS=["testserver"])
class DataDocumentDetailTest(TransactionTestCase):
    fixtures = fixtures_standard

    def setUp(self):
        self.client.login(username="Karyn", password="specialP@55word")

    def test_user_availability(self):
        self.client.logout()
        doc = DataDocument.objects.get(pk=254780)
        response = self.client.get(f"/datadocument/{doc.pk}/")
        self.assertEqual(
            response.status_code, 200, "The page must return a 200 status code"
        )
        page = html.fromstring(response.content)
        self.assertFalse(page.xpath('//*[@id="add_product_button"]'))
        self.assertFalse(page.xpath('//*[@id="edit_document"]'))
        self.assertFalse(page.xpath('//*[@id="delete_document"]'))
        self.assertFalse(page.xpath('//*[@id="btn-add-or-edit-extracted-text"]'))
        self.assertIsNone(page.xpath('//*[@id="qa_icon_unchecked"]')[0].get("href"))
        self.assertFalse(page.xpath('//*[@id="add_chemical"]'))
        self.assertIsNone(page.xpath('//*[@id="datasource_link"]')[0].get("href"))
        self.assertIsNone(page.xpath('//*[@id="datagroup_link"]')[0].get("href"))
        # check that all associated links redirect to login when used
        response = self.client.get(f"/datadocument/edit/{doc.pk}/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)
        response = self.client.get(f"/datadocument/delete/{doc.pk}/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)
        response = self.client.get(f"/link_product_form/{doc.pk}/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)
        response = self.client.get(f"/extractedtext/edit/{doc.pk}/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)
        response = self.client.get(f"/qa/extractedtext/{doc.pk}/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)
        response = self.client.get(f"/chemical/{doc.pk}/create/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)
        response = self.client.get(
            f"/chemical/doc.extractedtext.rawchem.first().pk/edit/"
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)
        response = self.client.get(f"/datagroup/{doc.data_group_id}/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)
        response = self.client.get(f"/datasource/{doc.data_group.data_source_id}/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_absent_extracted_text(self):
        # Check every data document and confirm that its detail page loads,
        # with or without a detail formset
        for dd in DataDocument.objects.exclude(data_group__group_type__code="SD"):
            ddid = dd.id
            resp = self.client.get("/datadocument/%s/" % ddid)
            self.assertEqual(
                resp.status_code, 200, "The page must return a 200 status code"
            )
            try:
                ExtractedText.objects.get(data_document=dd)
            except ExtractedText.DoesNotExist:
                self.assertContains(
                    resp, "No Extracted Text exists for this Data Document"
                )
            else:
                self.assertContains(resp, "<b>Extracted Text</b>")

    def test_curated_chemical(self):
        """
        The correct values appear on the page for RawChem records
        that have been matched to DSSToxLookup records, and
        the curated name and CAS appear in the sidebar navigation
        """
        ddid = 7
        resp = self.client.get(f"/datadocument/%s/cards" % ddid)
        self.assertIn('href="/chemical/DTXSID2021781/"', resp.content.decode("utf-8"))
        # Any curated chemicals should also be linked to COMPTOX
        self.assertIn(
            "https://comptox.epa.gov/dashboard/dsstoxdb/results?search=DTXSID2021781",
            resp.content.decode("utf-8"),
        )

        page = html.fromstring(resp.content)
        # The raw chem name is different from the curated chem name,
        # so the right-side navigation link should NOT match the card
        # h3 element
        card_chemname = page.xpath('//*[@id="raw_chem_name-4"]//*')[0].text
        nav_chemname = page.xpath('//*[@id="chem-scrollspy"]/ul/li/a/p')[0].text
        self.assertFalse(
            card_chemname == nav_chemname,
            "The card and the scrollspy should show different chem names",
        )

        # Test presence of necessary display attributes
        raw_comp = page.xpath('//*[@id="raw_comp"]')[0].text
        self.assertInHTML("4 - 7 weight fraction", raw_comp)
        report_funcuse = page.xpath('//*[@id="functional_uses_1"]//*')[0].text
        self.assertIn("swell", report_funcuse)
        ingredient_rank = page.xpath('//*[@id="ingredient_rank"]')[0].text
        self.assertIn("1", ingredient_rank)

    def test_script_links(self):
        doc = DataDocument.objects.get(pk=156051)
        response = self.client.get(doc.get_absolute_url())
        self.assertContains(response, "Extraction script")
        self.assertContains(response, "Download Script")
        self.assertContains(response, "Cleaning Script")
        comptox = "https://comptox.epa.gov/dashboard/dsstoxdb/results?search="
        response = self.client.get(f"/datadocument/{doc.pk}/cards")
        self.assertContains(response, comptox)
        chems = doc.extractedtext.rawchem.all().select_subclasses()
        for chem in chems:
            chem.script = None
            chem.save()
        response = self.client.get(doc.get_absolute_url())
        self.assertNotContains(response, "Cleaning Script")

    def test_product_card_location(self):
        response = self.client.get("/datadocument/179486/")
        html = response.content.decode("utf-8")
        e_idx = html.index('id="extracted-text-title"')
        p_idx = html.index('id="product-title"')
        self.assertTrue(
            p_idx < e_idx, ("Product card should come before " "Extracted Text card")
        )

    def test_product_create_link(self):
        response = self.client.get("/datadocument/167497/")
        self.assertContains(response, "/link_product_form/167497/")
        data = {
            "title": ["New Product"],
            "upc": ["stub_9860"],
            "document_type": ["29"],
            "return_url": ["/datadocument/167497/"],
        }
        response = self.client.post("/link_product_form/167497/", data=data)
        self.assertRedirects(response, "/datadocument/167497/")
        response = self.client.get(response.url)
        self.assertContains(response, "New Product")

    def test_no_product_create_link(self):
        # GroupTypes that should have no products associated.
        product_restricted_codes = ["CP", "HH", "HP", "FU"]

        docs = DataDocument.objects.filter(
            data_group__group_type__code__in=product_restricted_codes
        )

        for doc in docs:
            if doc.data_group.type in product_restricted_codes:
                response = self.client.get("/datadocument/" + str(doc.pk) + "/")
                self.assertNotContains(
                    response,
                    "/link_product_form/",
                    msg_prefix=f"{doc.data_group.type} contains a link_product_form href",
                )

                product_restricted_codes.remove(doc.data_group.type)

                # If all restricted types have been checked, break.
                if not product_restricted_codes:
                    break

    def test_product_title_duplication(self):
        response = self.client.get("/datadocument/245401/")
        self.assertContains(response, "/link_product_form/245401/")
        # Add a new Product
        data = {
            "title": ["Product Title"],
            "upc": ["stub_9100"],
            "document_type": ["29"],
            "return_url": ["/datadocument/245401/"],
        }
        response = self.client.post("/link_product_form/245401/", data=data)
        self.assertRedirects(response, "/datadocument/245401/")
        response = self.client.get(response.url)
        new_product = Product.objects.get(upc="stub_9100")
        self.assertContains(response, f"product/%s" % new_product.id)

        # Add another new Product with the same title
        data = {
            "title": ["Product Title"],
            "upc": ["stub_9101"],
            "document_type": ["29"],
            "return_url": ["/datadocument/245401/"],
        }
        response = self.client.post("/link_product_form/245401/", data=data)
        self.assertRedirects(response, "/datadocument/245401/")
        response = self.client.get(response.url)
        new_product = Product.objects.get(upc="stub_9101")
        self.assertContains(response, f"product/%s" % new_product.id)

    def test_extracted_icon(self):

        doc = DataDocument.objects.get(pk=254780)
        response = self.client.get(f"/datadocument/{doc.pk}/")
        page = html.fromstring(response.content)
        self.assertFalse(doc.extractedtext.qa_checked)
        self.assertFalse(page.xpath('//*[@id="qa_icon_checked"]'))
        self.assertTrue(page.xpath('//*[@id="qa_icon_unchecked"]'))
        et = doc.extractedtext
        et.qa_checked = True
        et.save()
        response = self.client.get(f"/datadocument/{doc.pk}/")
        page = html.fromstring(response.content)
        self.assertTrue(doc.extractedtext.qa_checked)
        self.assertFalse(page.xpath('//*[@id="qa_icon_unchecked"]'))
        self.assertTrue(page.xpath('//*[@id="qa_icon_checked"]'))
        et.delete()
        doc.refresh_from_db()
        response = self.client.get(f"/datadocument/{doc.pk}/")
        page = html.fromstring(response.content)
        self.assertFalse(doc.is_extracted)
        self.assertFalse(page.xpath('//*[@id="qa_icon_unchecked"]'))
        self.assertFalse(page.xpath('//*[@id="qa_icon_checked"]'))

    def test_add_extracted(self):
        """Check that the user has the ability to create an extracted record
        when the document doesn't yet have an extracted record for data
        group types 'CP' and 'HH'
        """
        doc = DataDocument.objects.get(pk=354784)
        self.assertFalse(
            doc.is_extracted, ("This document is matched " "but not extracted")
        )
        data = {"hhe_report_number": ["47"]}
        self.client.post("/extractedtext/edit/354784/", data=data)
        doc.refresh_from_db()
        self.assertTrue(doc.is_extracted, "This document should be extracted ")
        response = self.client.get(reverse("data_document", args=[doc.pk]))
        response_html = html.fromstring(response.content.decode("utf8"))
        hhe_no = response_html.xpath('//*[@id="id_hhe_report_number"]')[0].text
        self.assertIn("47", hhe_no)

    def test_delete(self):
        doc_pk = 354784
        doc = DataDocument.objects.get(pk=doc_pk)
        post_uri = reverse("data_document_delete", args=[doc_pk])

        def doc_exists():
            return DataDocument.objects.filter(pk=doc_pk).exists()

        doc.file.save(
            name="document_sample_file.pdf",
            content=open(
                "sample_files/images/datadocuments/document_sample_file.pdf", "rb"
            ),
            save=True,
        )

        self.assertTrue(
            doc_exists(), "Document does not exist prior to delete attempt."
        )

        self.assertTrue(
            os.path.exists(doc.file.path), "the stored file should be in MEDIA_ROOT"
        )

        self.client.post(post_uri)
        self.assertFalse(doc_exists(), "Document still exists after delete attempt.")

        self.assertTrue(
            os.path.exists(doc.file.path),
            "the stored file should exist in MEDIA_ROOT even after document is deleted.",
        )

    def test_ingredient_rank(self):
        doc = DataDocument.objects.get(pk=254643)
        qs = doc.extractedtext.rawchem.select_subclasses()
        one = qs.first()
        two = qs.last()
        self.assertTrue(two.ingredient_rank > one.ingredient_rank)
        response = self.client.get(f"/datadocument/{doc.pk}/cards")
        html = response.content.decode("utf-8")
        first_idx = html.index(f'id="chem-card-{one.pk}"')
        second_idx = html.index(f'id="chem-card-{two.pk}"')
        self.assertTrue(
            second_idx > first_idx,
            ("Ingredient rank 1 comes before " "Ingredient rank 2"),
        )

    def test_title_ellipsis(self):
        """Check that DataDocument title gets truncated"""
        trunc_length = 45
        doc = DataDocument.objects.filter(
            title__iregex=(".{%i,}" % (trunc_length + 1))
        ).first()
        self.assertIsNotNone(
            doc,
            ("No DataDocument found with a title greater" " than %i characters.")
            % trunc_length,
        )
        response = self.client.get("/datadocument/%i/" % doc.id)
        response_html = html.fromstring(response.content)
        trunc_title = doc.title[: trunc_length - 1] + "…"
        html_title = response_html.xpath('//*[@id="title"]/h1')[0].text
        self.assertEqual(trunc_title, html_title, "DataDocument title not truncated.")

    def test_subtitle_ellipsis(self):
        id = 354783
        response = self.client.get("/datadocument/%i/" % id)
        # Confirm that the displayed subtitle is truncated and ... is appended
        self.assertContains(response, "This subtitle is more than 90 c…")

    def test_hp_group_type(self):
        id = 53
        response = self.client.get("/datadocument/%i/" % id)
        # Should display organization for HP group type
        self.assertContains(response, "Test Organization")
        # Should not display Product name
        self.assertNotContains(response, "Product name")

    def test_raw_category_ellipsis(self):
        id = 354784
        response = self.client.get("/datadocument/%i/" % id)
        # Confirm that the raw category is truncated and ... is appended
        self.assertContains(response, "Purple haze all in my brain, lately…")

    def _get_icon_span(self, doc_id):
        doc = DataDocument.objects.get(pk=doc_id)
        response = self.client.get(f"/datadocument/{doc.pk}/")
        h = html.fromstring(response.content.decode("utf8"))
        return h.xpath("//a[contains(@href, '%s')]/span" % doc.file.name)[0].values()[0]

    def test_icons(self):
        icon_span = self._get_icon_span(173396)
        self.assertEqual("fa fa-fs fa-file-word", icon_span)
        icon_span = self._get_icon_span(173824)
        self.assertEqual("fa fa-fs fa-file-image", icon_span)
        icon_span = self._get_icon_span(174238)
        self.assertEqual("fa fa-fs fa-file-word", icon_span)
        icon_span = self._get_icon_span(176163)
        self.assertEqual("fa fa-fs fa-file", icon_span)
        icon_span = self._get_icon_span(176257)
        self.assertEqual("fa fa-fs fa-file-image", icon_span)
        icon_span = self._get_icon_span(177774)
        self.assertEqual("fa fa-fs fa-file-excel", icon_span)
        icon_span = self._get_icon_span(177852)
        self.assertEqual("fa fa-fs fa-file-csv", icon_span)
        icon_span = self._get_icon_span(178456)
        self.assertEqual("fa fa-fs fa-file-excel", icon_span)
        icon_span = self._get_icon_span(178496)
        self.assertEqual("fa fa-fs fa-file-alt", icon_span)
        icon_span = self._get_icon_span(172462)
        self.assertEqual("fa fa-fs fa-file-pdf", icon_span)

    def test_last_updated(self):
        extracted = ExtractedComposition.objects.filter(updated_at__isnull=False)
        response = self.client.get(
            f"/datadocument/{extracted.first().extracted_text.data_document.pk}/cards"
        )
        self.assertContains(response, "Last updated:")

        extracted = ExtractedListPresence.objects.filter(updated_at__isnull=False)
        response = self.client.get(
            f"/datadocument/{extracted.first().extracted_text.data_document.pk}/cards"
        )
        self.assertContains(response, "Last updated:")

        extracted = ExtractedComposition.objects.filter(updated_at__isnull=True).first()
        self.assertTrue(extracted.updated_at == None)
        extracted.ingredient_rank = 1
        extracted.save()
        extracted.refresh_from_db()
        self.assertTrue(extracted.updated_at != None)

        extracted = ExtractedListPresence.objects.filter(
            updated_at__isnull=True
        ).first()
        self.assertTrue(extracted.updated_at == None)
        extracted.qa_flag = 1
        extracted.save()
        extracted.refresh_from_db()
        self.assertTrue(extracted.updated_at != None)

    def test_epa_reg_number(self):
        id = 7
        doc = DataDocument.objects.get(pk=id)
        reg_no = doc.epa_reg_number
        response = self.client.get(doc.get_absolute_url())
        self.assertContains(response, reg_no)

    def test_download_chemicals(self):
        # download button for CP type
        cp_doc = DataDocument.objects.filter(data_group__group_type__code="CP").first()
        response = self.client.get(f"/datadocument/{cp_doc.pk}/")
        page = html.fromstring(response.content)
        download_button = page.xpath('//*[@id="download_chemicals"]')
        self.assertEqual(
            1, len(download_button), "download button available for CP types"
        )
        # download stream
        response = self.client.get(f"/datadocument/{cp_doc.pk}/download_chemicals/")
        self.assertEqual(200, response.status_code)
        self.assertIsNotNone(response.streaming_content)

        # download button not exist for non CP type
        non_cp_doc = DataDocument.objects.filter(
            data_group__group_type__code="CO"
        ).first()
        response = self.client.get(f"/datadocument/{non_cp_doc.pk}/")
        page = html.fromstring(response.content)
        download_button = page.xpath('//*[@id="download_chemicals"]')
        self.assertEqual(
            0, len(download_button), "download button not available for non CP types"
        )
        response = self.client.get(f"/datadocument/{non_cp_doc.pk}/download_chemicals/")
        # download blocked for non CP type
        self.assertEqual(400, response.status_code)


class TestDynamicDetailFormsets(TestCase):
    fixtures = fixtures_standard

    def setUp(self):
        self.client.login(username="Karyn", password="specialP@55word")

    def test_extractedsubclasses(self):
        """Confirm that the inheritance manager is returning appropriate
        subclass objects and ExtractedText base class objects
        """
        for doc in DataDocument.objects.all():
            try:
                extsub = ExtractedText.objects.get_subclass(data_document=doc)
                # A document with the CP data group type should be linked to
                # ExtractedCPCat objects
                if doc.data_group.group_type.code == "CP":
                    self.assertEqual(type(extsub), ExtractedCPCat)
                elif doc.data_group.group_type.code == "HH":
                    self.assertEqual(type(extsub), ExtractedHHDoc)
                else:
                    self.assertEqual(type(extsub), ExtractedText)
            except ObjectDoesNotExist:
                pass

    def test_every_extractedtext(self):
        """'Loop through all the ExtractedText objects and confirm that the new
        create_detail_formset method returns forms based on the correct models
        """
        for et in ExtractedText.objects.all():
            dd = et.data_document
            ParentForm, ChildForm = create_detail_formset(dd, settings.EXTRA)
            child_formset = ChildForm(instance=et)
            # Compare the model of the child formset's QuerySet to the model
            # of the ExtractedText object's child objects
            dd_child_model = get_extracted_models(dd.data_group.group_type.code)[1]
            childform_model = child_formset.__dict__.get("queryset").__dict__.get(
                "model"
            )
            self.assertEqual(dd_child_model, childform_model)

    def test_cp_form_contains_correct_fields(self):
        """
        Test to verify that the form for Data Documents of type 'CP'
        can only have specific fields.
        Outlined in issue #1208 https://github.com/HumanExposure/factotum/issues/1208
        """
        acceptable_fields = ["doc_date"]

        cp_data_doc = DataDocument.objects.filter(
            data_group__group_type__code="CP"
        ).first()
        parent_form, _ = create_detail_formset(cp_data_doc)

        # Assert all acceptable fields are in the Extracted Text form.
        for field in acceptable_fields:
            self.assertIn(field, parent_form.base_fields)

        # Assert ONLY the acceptable fields are in the Extracted Text form.
        for field in parent_form.base_fields:
            self.assertIn(field, acceptable_fields)

    def test_listpresence_tags_form(self):
        """'Assure that the list presence keywords appear for correct doc types and tags save"""
        for code, model in datadocument_models.items():
            if DataDocument.objects.filter(
                data_group__group_type__code=code, extractedtext__isnull=False
            ):
                doc = DataDocument.objects.filter(
                    data_group__group_type__code=code, extractedtext__isnull=False
                ).first()
                response = self.client.get(
                    reverse("data_document", kwargs={"pk": doc.pk})
                )
                response_html = html.fromstring(response.content.decode("utf8"))
                if code == "CP":
                    self.assertTrue(
                        response_html.xpath('boolean(//*[@id="id_tags"])'),
                        "Tag input should exist for Chemical Presence doc type",
                    )
                    elpt_count = ExtractedListPresenceTag.objects.count()
                    # seed data contains 2 tags for the 50 objects in this document
                    elp2t_count = ExtractedListPresenceToTag.objects.count()
                    # This post should preseve the 2 existing tags and add 4 more
                    self.client.post(
                        path=reverse("save_tag_form", kwargs={"pk": doc.pk}),
                        data={
                            "tags": ExtractedListPresenceTag.objects.filter(
                                name__in=[
                                    "after_shave",
                                    "agrochemical",
                                    "flavor",
                                    "slimicide",
                                ]
                            ).values_list("pk", flat=True),
                            "chems": doc.extractedtext.rawchem.values_list(
                                "pk", flat=True
                            ),
                        },
                    )
                    # Total number of tags should not have changed
                    self.assertEqual(
                        ExtractedListPresenceTag.objects.count(), elpt_count
                    )
                    # But the tagged relationships should have increased by 4 * the number of list presence objects
                    self.assertEqual(
                        ExtractedListPresenceToTag.objects.count(),
                        elp2t_count
                        + (
                            4
                            * doc.extractedtext.rawchem.select_subclasses(
                                "extractedlistpresence"
                            ).count()
                        ),
                    )
                elif code == "HP":
                    # These test are currently in integration/test_hp_card.py
                    pass
                else:
                    self.assertFalse(
                        response_html.xpath('boolean(//*[@id="id_tags"])'),
                        "Tag input should only exist for Chemical Presence doc type",
                    )

    def test_listpresence_tag_curation(self):
        """'Assure that the list presence keyword link appears in nav,
        and correct docs are listed on the page
        """
        response = self.client.get(reverse("index"))
        self.assertContains(
            response, 'href="' + reverse("list_presence_tag_curation") + '"'
        )

        # seed data should have one data document with a chemical, but no tags
        response = self.client.get(reverse("list_presence_tag_curation"))
        self.assertContains(response, 'href="/datadocument/354786/' + '"')

        # add a tag and make sure none get returned
        ExtractedListPresenceToTag.objects.create(content_object_id=854, tag_id=323)
        response = self.client.get(reverse("list_presence_tag_curation"))
        self.assertNotContains(response, 'href="/datadocument/354786/' + '"')

    def test_missing_raw_chem_names(self):
        # Add new HHRec object with no raw_chem_name
        ext = ExtractedText.objects.get(data_document_id=354782)
        hhrec = ExtractedHHRec(
            sampling_method="test sampling method", extracted_text=ext
        )
        hhrec.save()
        response = self.client.get("/datadocument/%i/cards" % ext.data_document_id)
        page = html.fromstring(response.content)
        raw_chem_name = page.xpath(
            '//*[@id="raw_chem_name-' + str(hhrec.id) + '"]/small'
        )[0].text
        self.assertIn("None", raw_chem_name)
        raw_cas = page.xpath('//*[@id="raw_cas-' + str(hhrec.id) + '"]/small')[0].text
        self.assertIn("None", raw_cas)

    def test_datadoc_datasource_url_links(self):
        # Check data document with datadoc and datasource URL links
        response = self.client.get("/datadocument/179486/")
        self.assertIn(
            "View source document (external)", response.content.decode("utf-8")
        )
        datadocURL = "http://airgas.com/msds/001088.pdf"
        self.assertContains(response, datadocURL)

        self.assertIn("View Data Source (external)", response.content.decode("utf-8"))
        datasourceURL = "http://www.airgas.com/sds-search"
        self.assertContains(response, datasourceURL)

    def test_component_label(self):
        data_document = DataDocument.objects.get(pk=254781)
        rawchem = RawChem.objects.get(pk=759)
        component = rawchem.component
        response = self.client.get("/datadocument/%i/cards" % data_document.pk)
        response_html = html.fromstring(response.content)
        component_text = response_html.xpath(
            f'//*[@id="component-{rawchem.id}"]/text()'
        ).pop()
        self.assertEqual("Component: " + component, component_text)

    def test_chemical_ordering(self):
        data_document = DataDocument.objects.get(pk=170415)
        exchems = ExtractedComposition.objects.filter(
            extracted_text_id=170415
        ).order_by("component", "ingredient_rank")
        chem_ids = exchems.values_list("id", flat=True)
        first_id = chem_ids[0]
        second_id = chem_ids[1]
        response = self.client.get("/datadocument/%i/cards" % data_document.pk)
        response_html = html.fromstring(response.content)
        cards = response_html.find_class("card")
        self.assertEqual(cards[0].get("id"), f"chem-card-{first_id}")

        # changing the component of the first chemical should move it to the bottom
        # of the page
        ec = exchems.get(id=93)
        ec.component = "Component C"
        ec.save()
        response = self.client.get("/datadocument/%i/cards" % data_document.pk)
        response_html = html.fromstring(response.content)
        cards = response_html.find_class("card")
        # the new first card should match the second ID
        self.assertEqual(cards[0].get("id"), f"chem-card-{second_id}")
        self.client.post(
            path=reverse("detected_flag_toggle_yes", kwargs={"doc_pk": 170415}),
            data={"chems": ["93", "557"]},
        )
        self.assertEqual(exchems.get(id=93).chem_detected_flag, "1")
        self.assertEqual(exchems.get(id=557).chem_detected_flag, "1")
        self.client.post(
            path=reverse("detected_flag_toggle_no", kwargs={"doc_pk": 170415}),
            data={"chems": ["93", "557"]},
        )
        self.assertEqual(exchems.get(id=93).chem_detected_flag, "0")
        self.assertEqual(exchems.get(id=557).chem_detected_flag, "0")
        self.client.post(
            path=reverse("detected_flag_reset", kwargs={"doc_pk": 170415}),
            data={"chems": ["93", "557"]},
        )
        self.assertEqual(exchems.get(id=93).chem_detected_flag, None)
        self.assertEqual(exchems.get(id=557).chem_detected_flag, None)

    def test_functional_use_chemical_cards(self):
        data_document = DataDocument.objects.get(pk=5)
        response = self.client.get("/datadocument/%i/" % data_document.pk)

        self.assertTemplateUsed("data_document/functional_use_cards.html")

    def test_organization_presence(self):
        for doc_id in [
            7,  # Composition
            5,  # Functional Use
            254781,  # Chemical Presence List
            354783,  # HHE Report
            54,  # Habits and Practices
            9,  # Literature Monitoring
        ]:
            doc = DataDocument.objects.get(pk=doc_id)
            response = self.client.get("/datadocument/edit/%i/" % doc_id)
            response_html = html.fromstring(response.content)
            self.assertTrue(
                response_html.xpath('boolean(//*[@id="id_organization"])'),
                "Organization should be editable for all doc types",
            )
            response = self.client.get("/datadocument/%i/" % doc_id)
            response_html = html.fromstring(response.content)
            self.assertEqual(
                response_html.xpath('//*[@id="organization"]')[0].text, doc.organization
            )

    def test_delete_tags(self):
        doc_id = 53
        # should have tags assigned initially
        tags_count = ExtractedHabitsAndPracticesToTag.objects.filter(
            content_object__extracted_text__data_document_id=doc_id
        ).count()
        self.assertTrue(tags_count > 0, "should have tags initially")
        # delete all tags
        self.client.post("/datadocument/%i/tags/delete/" % doc_id)
        # should have no tags assigned now
        tags_count = ExtractedHabitsAndPracticesToTag.objects.filter(
            content_object__extracted_text__data_document_id=doc_id
        ).count()
        self.assertEqual(0, tags_count, "should removed all tags")
