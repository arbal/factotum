from django.db.models import Max
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait

from dashboard.models import RawChem, AuditLog
from dashboard.tests.loader import fixtures_standard, load_browser
from django.contrib.staticfiles.testing import StaticLiveServerTestCase


def log_karyn_in(object):
    """
    Log user in for further testing.
    """
    object.browser.get(object.live_server_url + "/login/")
    body = object.browser.find_element_by_tag_name("body")
    object.assertIn("Please sign in", body.text)
    username_input = object.browser.find_element_by_name("username")
    username_input.send_keys("Karyn")
    password_input = object.browser.find_element_by_name("password")
    password_input.send_keys("specialP@55word")
    object.browser.find_element_by_class_name("btn").click()


class TestCuratedChemicalRemoval(StaticLiveServerTestCase):
    fixtures = fixtures_standard

    def setUp(self):
        self.browser = load_browser()
        log_karyn_in(self)

    def tearDown(self):
        self.browser.quit()

    def test_index_page_table(self):
        index_url = self.live_server_url + "/curated_chemical_removal/"
        self.browser.get(index_url)

        self.wait = WebDriverWait(self.browser, 10)
        search_form = self.wait.until(
            expected_conditions.presence_of_element_located((By.ID, "search_chem_form"))
        )
        with self.assertRaises(NoSuchElementException):
            self.browser.find_element_by_id("curated_chemicals_info")

        # search chlorine
        search_form.find_element_by_id("search_chem_text").send_keys("chlorine\n")
        self.wait.until(
            expected_conditions.text_to_be_present_in_element(
                (By.ID, "curated_chemicals_info"), "Showing 1 to 1 of 1 entries"
            )
        )
        sid_cell = self.browser.find_element_by_xpath(
            '//*[@id="curated_chemicals"]/tbody/tr[1]/td[1]'
        )
        raw_name_cell = self.browser.find_element_by_xpath(
            '//*[@id="curated_chemicals"]/tbody/tr[1]/td[2]'
        )
        raw_cas_cell = self.browser.find_element_by_xpath(
            '//*[@id="curated_chemicals"]/tbody/tr[1]/td[3]'
        )
        curated_name_cell = self.browser.find_element_by_xpath(
            '//*[@id="curated_chemicals"]/tbody/tr[1]/td[4]'
        )
        curated_cas_cell = self.browser.find_element_by_xpath(
            '//*[@id="curated_chemicals"]/tbody/tr[1]/td[5]'
        )
        count_cell = self.browser.find_element_by_xpath(
            '//*[@id="curated_chemicals"]/tbody/tr[1]/td[6]'
        )
        detail_link = self.browser.find_element_by_xpath(
            '//*[@id="curated_chemicals"]/tbody/tr[1]/td[6]/a'
        )
        self.assertIn("DTXSID1020273", sid_cell.text)
        self.assertIn("Chlorine", raw_name_cell.text)
        self.assertIn("7782-50-5", raw_cas_cell.text)
        self.assertIn("chlorine", curated_name_cell.text)
        self.assertIn("7782-50-5", curated_cas_cell.text)
        self.assertEqual("3", count_cell.text)
        self.assertIn(
            "/curated_chemical_detail/DTXSID1020273?raw_chem_name=Chlorine&raw_cas=7782-50-5",
            detail_link.get_attribute("href"),
        )

    def test_detail_page(self):
        sid = "DTXSID1020273"
        raw_chem_name = "Chlorine"
        raw_cas = "7782-50-5"

        # set one chemical sid provisional flag
        chem = RawChem.objects.get(pk=24)
        chem.provisional = True
        chem.save()
        sid_audit = (
            AuditLog.objects.filter(rawchem_id=24, field_name="sid").annotate(
                latest_update=Max("date_created")
            )
        ).first()

        detail_url = (
            self.live_server_url
            + f"/curated_chemical_detail/{sid}?raw_chem_name={raw_chem_name}&raw_cas={raw_cas}"
        )
        self.browser.get(detail_url)

        self.wait = WebDriverWait(self.browser, 10)
        self.wait.until(
            expected_conditions.text_to_be_present_in_element(
                (By.ID, "curated_chemicals_info"), "Showing 1 to 3 of 3 entries"
            )
        )
        self.assertEqual(sid, self.browser.find_element_by_id("sid").text)
        self.assertEqual(
            raw_chem_name, self.browser.find_element_by_id("raw_chem_name").text
        )
        self.assertEqual(raw_cas, self.browser.find_element_by_id("raw_cas").text)

        document_cell = self.browser.find_element_by_xpath(
            '//*[@id="curated_chemicals"]/tbody/tr[1]/td[1]'
        )
        document_link = self.browser.find_element_by_xpath(
            '//*[@id="curated_chemicals"]/tbody/tr[1]/td[1]/a'
        )
        sid_update_cell = self.browser.find_element_by_xpath(
            '//*[@id="curated_chemicals"]/tbody/tr[1]/td[2]'
        )
        provisional_cell = self.browser.find_element_by_xpath(
            '//*[@id="curated_chemicals"]/tbody/tr[1]/td[3]'
        )
        self.assertIn(chem.extracted_text.data_document.title, document_cell.text)
        self.assertIn(
            "/datadocument/245048/#chem-card-24", document_link.get_attribute("href")
        )
        self.assertEqual(
            sid_audit.latest_update.strftime("%b %d, %Y, %I:%M:%S %p"),
            sid_update_cell.text,
        )
        self.assertEqual("Yes", provisional_cell.text)

        # test provisional filter
        provisional_select = self.browser.find_element_by_id("provisional_dropdown")
        Select(provisional_select).select_by_value("1")
        self.wait.until(
            expected_conditions.text_to_be_present_in_element(
                (By.ID, "curated_chemicals_info"),
                "Showing 1 to 1 of 1 entries (filtered from 3 total entries)",
            )
        )
        Select(provisional_select).select_by_value("0")
        self.wait.until(
            expected_conditions.text_to_be_present_in_element(
                (By.ID, "curated_chemicals_info"),
                "Showing 1 to 2 of 2 entries (filtered from 3 total entries)",
            )
        )

    def test_delete_linkage(self):
        index_url = self.live_server_url + "/curated_chemical_removal/"
        self.browser.get(index_url)

        self.wait = WebDriverWait(self.browser, 10)
        search_form = self.wait.until(
            expected_conditions.presence_of_element_located((By.ID, "search_chem_form"))
        )
        with self.assertRaises(NoSuchElementException):
            self.browser.find_element_by_id("curated_chemicals_info")

        # clear audit log
        AuditLog.objects.all().delete()
        # search chlorine
        search_form.find_element_by_id("search_chem_text").send_keys("chlorine\n")
        self.wait.until(
            expected_conditions.text_to_be_present_in_element(
                (By.ID, "curated_chemicals_info"), "Showing 1 to 1 of 1 entries"
            )
        )
        remove_button = self.browser.find_element_by_class_name("delete-linkage-btn")
        remove_button.click()
        self.wait.until(
            expected_conditions.element_to_be_clickable(
                (By.ID, "remove-linkage-confirm-btn")
            )
        )
        confirm_button = self.browser.find_element_by_id("remove-linkage-confirm-btn")
        confirm_button.click()
        self.wait.until(
            expected_conditions.text_to_be_present_in_element(
                (By.CLASS_NAME, "alert-success"),
                "Raw chemical Chlorine/7782-50-5 linkages to curated chemical DTXSID1020273 have been removed",
            )
        )
        rc_uncurated = RawChem.objects.filter(
            raw_chem_name="chlorine", raw_cas="7782-50-5"
        )
        raw_chem = rc_uncurated.first()
        self.assertEqual(raw_chem.dsstox, None)

        # Removing the dsstox reference should also cause the
        # `provisional` attribute to be nulled out
        # for rc in rc_uncurated:
        #     print(f"{rc.id}: provisional is {rc.provisional}, dsstox is {rc.dsstox}")

        rc_provisional = rc_uncurated.filter(provisional=True)
        self.assertIsNone(
            rc_provisional.first(),
            "All of the now-uncurated records should have provisional=False",
        )

        audit_entry = AuditLog.objects.first()
        self.assertIsNotNone(audit_entry)
        self.assertEqual(audit_entry.field_name, "sid")
        self.assertEqual(audit_entry.old_value, "DTXSID1020273")
