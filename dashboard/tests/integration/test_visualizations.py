import time
from django.test import tag
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.utils.decorators import classproperty
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

from dashboard.models import DSSToxLookup, PUC
from dashboard.tests.loader import fixtures_standard, load_browser


class TestVisualizations(StaticLiveServerTestCase):
    @classproperty
    def visualization_url(cls):
        return cls.live_server_url + "/visualizations"

    fixtures = fixtures_standard

    def setUp(self):
        self.browser = load_browser()

    def tearDown(self):
        self.browser.quit()

    def _n_children(self, tree):
        cnt = len(tree.children)
        for c in tree.children:
            cnt += self._n_children(c)
        return cnt

    @tag("puc")
    def test_bubble_plot(self):
        pucs = (
            PUC.objects.filter(kind__code__in=["FO", "AR", "OC"])
            .filter(cumulative_products_per_puc__cumulative_product_count__gt=0)
            .astree()
        )
        num_pucs = self._n_children(pucs)
        self.browser.get(self.visualization_url)
        wait = WebDriverWait(self.browser, 10)
        wait.until(ec.presence_of_element_located((By.CLASS_NAME, "bubble")))
        bubbles = self.browser.find_elements_by_class_name("bubble")
        self.assertTrue(num_pucs > 0, "Need more than one PUC")
        self.assertTrue(len(bubbles) > 0, "Need more than one bubble")
        self.assertEqual(
            num_pucs, len(bubbles), "There should be a circle drawn for every PUC"
        )
        plots = self.browser.find_elements_by_class_name("nestedcircles")
        self.assertTrue(len(plots) == 3, "Need more than one bubble")

    @tag("puc")
    def test_bubble_legend(self):
        self.browser.get(self.visualization_url)
        wait = WebDriverWait(self.browser, 10)
        wait.until(ec.presence_of_element_located((By.ID, "puc-accordion-FO")))
        bubble_legend = self.browser.find_element_by_id("puc-accordion-FO")
        self.assertTrue(bubble_legend, "FO Bubble plot legend could not be found")
        child_card = bubble_legend.find_element_by_xpath("//*[@id='accordion-20']")
        self.assertEqual(child_card.get_attribute("class"), "collapse")
        bubble_legend = self.browser.find_element_by_id("puc-accordion-AR")
        self.assertTrue(bubble_legend, "AR Bubble plot legend could not be found")
        # we are no longer displaying legend items with no circles
        # child_card = bubble_legend.find_element_by_xpath("//*[@id='accordion-316']")
        # self.assertEqual(child_card.get_attribute("class"), "collapse")
        # bubble_legend = self.browser.find_element_by_id("puc-accordion-OC")
        # self.assertTrue(bubble_legend, "OC Bubble plot legend could not be found")
        # child_card = bubble_legend.find_element_by_xpath("//*[@id='accordion-319']")
        # self.assertEqual(child_card.get_attribute("class"), "collapse")

    @tag("puc")
    def test_collapsible_tree(self):
        pucs = PUC.objects.filter(kind__code="FO").astree()
        num_pucs = self._n_children(pucs)
        self.browser.get(self.visualization_url)
        wait = WebDriverWait(self.browser, 10)
        wait.until(ec.presence_of_element_located((By.CLASS_NAME, "tree-node")))
        nodes = self.browser.find_elements_by_class_name("tree-node")
        self.assertTrue(num_pucs > 0, "Need more than one PUC")
        self.assertTrue(len(nodes) > 0, "Need more than one node")

    @tag("puc")
    def test_dtxsid_bubble_plot(self):
        dss = DSSToxLookup.objects.get(sid="DTXSID9022528")
        self.browser.get(self.live_server_url + dss.get_absolute_url())

        time.sleep(3)

        num_pucs = dss.get_cumulative_puc_count()
        bubbles = self.browser.find_elements_by_class_name("bubble")
        self.assertEqual(
            num_pucs, len(bubbles), "There should be a circle drawn for every PUC"
        )

    @tag("puc")
    def test_venn_diagram(self):
        self.browser.get(self.visualization_url)
        wait = WebDriverWait(self.browser, 10)
        wait.until(ec.presence_of_element_located((By.ID, "venn")))
        circles = self.browser.find_elements_by_class_name("venn-circle")
        intersections = self.browser.find_elements_by_class_name("venn-intersection")
        self.assertTrue(len(intersections) > 0, "Should have intersections")
