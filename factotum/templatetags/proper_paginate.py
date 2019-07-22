# This code adapted from https://medium.com/@sumitlni/paginate-properly-please-93e7ca776432

from django import template
import re

register = template.Library()


@register.filter(name="link_name")
def link_name(path, page_number):
    output = re.search("(page=\d+)", path)
    if output is not None:
        return path.replace(str(output.group(1)), f"page={page_number}")
    page_number = str(page_number)
    if "?" in path:
        return path + "&page=" + page_number
    return path + "?page=" + page_number


@register.filter(name="proper_paginate")
def proper_paginate(paginator, current_page, neighbors=4):
    if paginator.num_pages > 2 * neighbors:
        start_index = max(1, current_page - neighbors)
        end_index = min(paginator.num_pages, current_page + neighbors)
        if end_index < start_index + 2 * neighbors:
            end_index = start_index + 2 * neighbors
        elif start_index > end_index - 2 * neighbors:
            start_index = end_index - 2 * neighbors
        if start_index < 1:
            end_index -= start_index
            start_index = 1
        elif end_index > paginator.num_pages:
            start_index -= end_index - paginator.num_pages
            end_index = paginator.num_pages
        page_list = [f for f in range(start_index, end_index + 1)]
        return page_list[: (2 * neighbors + 1)]
    return paginator.page_range
