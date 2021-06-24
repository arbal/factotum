import os
import subprocess

from django.test import SimpleTestCase
from django.conf import settings
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from apps_api.core.pagination import StandardPagination


class ExamplePagination(StandardPagination):
    page_size = 5


class TestLint(SimpleTestCase):

    lint_dirs = [
        os.path.join(settings.BASE_DIR, "apps_api"),
        # os.path.join(settings.BASE_DIR, "factotum"),
    ]

    def test_black(self):
        cmd = subprocess.run(["black", "--check", "-q"] + self.lint_dirs)
        self.assertEqual(cmd.returncode, 0, "Files not formatted with black.")

    def test_pyflakes(self):
        cmd = subprocess.run(["pyflakes"] + self.lint_dirs)
        self.assertEqual(cmd.returncode, 0, "Linting errors found by pyflakes.")


class TestStandardPagination(SimpleTestCase):
    """
    Unit tests for `pagination.StandardPagination`.
    """

    pagination = ExamplePagination()
    queryset = range(1, 104)
    factory = APIRequestFactory()

    def paginate_queryset(self, request):
        return list(self.pagination.paginate_queryset(self.queryset, request))

    def get_paginated_content(self, queryset):
        response = self.pagination.get_paginated_response(queryset)
        return response.data

    def get_html_context(self):
        return self.pagination.get_html_context()

    def test_no_page_number(self):
        request = Request(self.factory.get("/"))
        queryset = self.paginate_queryset(request)
        content = self.get_paginated_content(queryset)
        self.assertEqual(queryset, [1, 2, 3, 4, 5])
        self.assertEqual(
            content,
            {
                "paging": {
                    "links": {
                        "current": "http://testserver/",
                        "first": "http://testserver/",
                        "last": "http://testserver/?page=21",
                        "next": "http://testserver/?page=2",
                        "previous": None,
                    },
                    "page": 1,
                    "pages": 21,
                    "size": 5,
                },
                "data": [1, 2, 3, 4, 5],
                "meta": {"count": 103},
            },
        )

    def test_second_page(self):
        request = Request(self.factory.get("/", {"page": 2}))
        queryset = self.paginate_queryset(request)
        content = self.get_paginated_content(queryset)
        self.assertEqual(queryset, [6, 7, 8, 9, 10])
        self.assertEqual(
            content,
            {
                "paging": {
                    "links": {
                        "current": "http://testserver/?page=2",
                        "first": "http://testserver/",
                        "last": "http://testserver/?page=21",
                        "next": "http://testserver/?page=3",
                        "previous": "http://testserver/",
                    },
                    "page": 2,
                    "pages": 21,
                    "size": 5,
                },
                "data": [6, 7, 8, 9, 10],
                "meta": {"count": 103},
            },
        )

    def test_last_page(self):
        request = Request(self.factory.get("/", {"page": 21}))
        queryset = self.paginate_queryset(request)
        content = self.get_paginated_content(queryset)
        self.assertEqual(queryset, [101, 102, 103])
        self.assertEqual(
            content,
            {
                "paging": {
                    "links": {
                        "current": "http://testserver/?page=21",
                        "first": "http://testserver/",
                        "last": "http://testserver/?page=21",
                        "next": None,
                        "previous": "http://testserver/?page=20",
                    },
                    "page": 21,
                    "pages": 21,
                    "size": 3,
                },
                "data": [101, 102, 103],
                "meta": {"count": 103},
            },
        )
