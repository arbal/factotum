from django.test import SimpleTestCase


class TestMetrics(SimpleTestCase):
    def tet_metrics_endpoint(self):
        response = self.client.get("/metrics")
        self.assertEqual(response.status_code, 200)
