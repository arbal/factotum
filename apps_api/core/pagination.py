from collections import OrderedDict

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.utils.urls import remove_query_param, replace_query_param


class StandardPagination(PageNumberPagination):
    """The pagination schema to attach to all paginated responses"""

    page_size_query_param = "page_size"
    max_page_size = 500

    def get_page_link(self, page_number, url=None):
        """Return a hyperlink to a given page"""
        if url is None:
            url = self.request.build_absolute_uri()
        if page_number == 1:
            return remove_query_param(url, self.page_query_param)
        return replace_query_param(url, self.page_query_param, page_number)

    def get_paginated_response(self, data):
        """Return the JSON payload"""
        page = self.page.number
        pages = self.page.paginator.num_pages
        links = OrderedDict(
            [
                ("current", self.get_page_link(page)),
                ("first", self.get_page_link(1)),
                ("last", self.get_page_link(pages)),
                ("next", self.get_next_link()),
                ("previous", self.get_previous_link()),
            ]
        )
        meta = OrderedDict([("count", self.page.paginator.count)])
        paging = OrderedDict(
            [
                ("links", links),
                ("page", page),
                ("pages", pages),
                ("size", len(self.page)),
            ]
        )
        out = OrderedDict([("paging", paging), ("data", data), ("meta", meta)])
        return Response(out)
