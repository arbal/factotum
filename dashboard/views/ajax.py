from django.http import HttpResponse, JsonResponse
from django.core import serializers
from dashboard.models import DataGroup, Product
import json


def product_ajax(request):

    draw = request.GET["draw"]
    start = int(request.GET["start"])
    length = int(request.GET["length"])
    length = 10
    order_column = int(request.GET["order[0][column]"])
    order_direction = "" if request.GET["order[0][dir]"] == "desc" else "-"
    column = [
        i.name for n, i in enumerate(Product._meta.get_fields()) if n == order_column
    ][0]
    global_search = request.GET["search[value]"]
    all_objects = Product.objects.all()

    columns = [
        "title",
        "brand_name",
        "prod_cat_id",
    ]  # TODO: change prod_cat_id to natural key
    objects = []
    for i in all_objects.order_by(order_direction + column)[
        start : start + length
    ].values():
        ret = [i[j] for j in columns]
        objects.append(ret)

    filtered_count = all_objects.count()
    total_count = Product.objects.count()
    return JsonResponse(
        {
            "recordsTotal": total_count,
            "recordsFiltered": filtered_count,
            "data": objects,
        }
    )
