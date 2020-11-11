from rest_framework_json_api.pagination import JsonApiPageNumberPagination

class LargeJsonApiPageNumberPagination(JsonApiPageNumberPagination):
    max_page_size = 1000