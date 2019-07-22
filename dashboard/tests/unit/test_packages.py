from django.test import SimpleTestCase


class PackageTest(SimpleTestCase):
    def test_packages(self):
        import django

        self.assertTrue(
            django.VERSION >= (2, 2),
            "Your django package could use a kick in the pants.",
        )
        self.assertTrue(
            django.VERSION < (2, 3), "Your django package has gotten ahead of itself."
        )
