from collections import OrderedDict

from django.conf import settings

from drf_yasg import inspectors, openapi
from uritemplate import expand

from apps_api.core import pagination

PY_CODE_SAMPLE = """
import requests

r = requests.get("%s")
r.json()
""".strip()

SHELL_CODE_SAMPLE = """
curl "%s"
""".strip()

RUBY_CODE_SAMPLE = """
require "net/http"
require "json"

uri = URI("%s")
response = Net::HTTP.get(uri)
JSON.parse(response)
""".strip()

R_CODE_SAMPLE = """
library(httr)

response <- GET("%s")
content(response, "parsed")
""".strip()


class StandardPaginatorInspector(inspectors.DjangoRestResponsePagination):
    def get_paginated_response(self, paginator, response_schema):
        if not isinstance(paginator, pagination.StandardPagination):
            return super().get_paginated_response(paginator, response_schema)

        if self.request:
            url = self.request.build_absolute_uri(self.path)
        else:
            url = self.path

        response_schema.description = "the requested data"
        links = openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties=OrderedDict(
                [
                    (
                        "current",
                        openapi.Schema(
                            type=openapi.TYPE_STRING,
                            format=openapi.FORMAT_URI,
                            example=(url + "?page=4"),
                        ),
                    ),
                    (
                        "first",
                        openapi.Schema(
                            type=openapi.TYPE_STRING,
                            format=openapi.FORMAT_URI,
                            example=url,
                        ),
                    ),
                    (
                        "last",
                        openapi.Schema(
                            type=openapi.TYPE_STRING,
                            format=openapi.FORMAT_URI,
                            example=(url + "?page=7"),
                        ),
                    ),
                    (
                        "next",
                        openapi.Schema(
                            type=openapi.TYPE_STRING,
                            format=openapi.FORMAT_URI,
                            x_nullable=True,
                            example=(url + "?page=5"),
                        ),
                    ),
                    (
                        "previous",
                        openapi.Schema(
                            type=openapi.TYPE_STRING,
                            format=openapi.FORMAT_URI,
                            x_nullable=True,
                            example=(url + "?page=3"),
                        ),
                    ),
                ]
            ),
            description="links to scroll through pages",
        )
        paging = openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties=OrderedDict(
                [
                    ("links", links),
                    (
                        "page",
                        openapi.Schema(
                            type=openapi.TYPE_INTEGER,
                            minimum=1,
                            description="current page number",
                            example=4,
                        ),
                    ),
                    (
                        "pages",
                        openapi.Schema(
                            type=openapi.TYPE_INTEGER,
                            minimum=1,
                            description="total number of pages",
                            example=7,
                        ),
                    ),
                    (
                        "size",
                        openapi.Schema(
                            type=openapi.TYPE_INTEGER,
                            minimum=0,
                            description="number of objects in this page",
                            example=100,
                        ),
                    ),
                ]
            ),
            description="information relating to pagination",
        )
        meta = openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties=OrderedDict(
                [
                    (
                        "count",
                        openapi.Schema(
                            type=openapi.TYPE_INTEGER,
                            minimum=0,
                            description="the total number of objects across all pages",
                            example=651,
                        ),
                    )
                ]
            ),
            description="information about this request",
        )
        schema = openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties=OrderedDict(
                [("paging", paging), ("data", response_schema), ("meta", meta)]
            ),
        )

        return schema

    def get_paginator_parameters(self, paginator):
        return [
            openapi.Parameter("page", "query", type=openapi.TYPE_INTEGER, minimum=1),
            openapi.Parameter(
                paginator.page_size_query_param,
                "query",
                type=openapi.TYPE_INTEGER,
                minimum=1,
                maximum=paginator.max_page_size,
                default=settings.REST_FRAMEWORK["PAGE_SIZE"],
            ),
        ]


class StandardAutoSchema(inspectors.SwaggerAutoSchema):
    def get_operation(self, operation_keys=None):
        operation = super().get_operation(operation_keys)
        if self.request:
            url = self.request.build_absolute_uri("/")[:-1] + self.path
        else:
            url = self.path
        # add code samples
        example_url = expand(url, id="3")
        operation["x-code-samples"] = [
            {"lang": "Python", "source": PY_CODE_SAMPLE % example_url},
            {"lang": "Shell", "source": SHELL_CODE_SAMPLE % example_url},
            {"lang": "Ruby", "source": RUBY_CODE_SAMPLE % example_url},
            {"lang": "R", "source": R_CODE_SAMPLE % example_url},
        ]
        return operation

    def get_operation_id(self, operation_keys):
        operation_id = super().get_operation_id(operation_keys)
        # make the operation camelCase
        components = operation_id.split("_")
        return components[0] + "".join(x.title() for x in components[1:])


class DjangoFiltersInspector(inspectors.FilterInspector):
    def get_filter_parameters(self, filter_backend):
        params = filter_backend.get_schema_operation_parameters(self.view)
        filters = filter_backend.get_filter_class(self.view)
        out = []
        if filters:
            filter_dict = filters.get_filters()
            for p in params:
                name = p.pop("name")
                in_ = p.pop("in")
                schema = p.pop("schema")
                extra = filter_dict[name].extra
                if "help_text" in extra:
                    p["description"] = extra["help_text"]
                else:
                    p.pop("description")
                if "initial" in extra:
                    p["example"] = extra["initial"]
                out.append(openapi.Parameter(name, in_, type=schema["type"], **p))
        return out
