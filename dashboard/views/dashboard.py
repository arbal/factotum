import csv
import datetime

from dateutil.relativedelta import relativedelta
from django.db.models import Count, DateField, DateTimeField, F
from django.db.models.functions import Trunc
from django.http import HttpResponse
from django.shortcuts import render

from dashboard.models import (
    PUC,
    DataDocument,
    ExtractedListPresenceTag,
    Product,
    ProductToPUC,
    RawChem,
    FunctionalUseCategory,
    News,
)


def get_stats():
    stats = {}
    stats["datadocument_count"] = DataDocument.objects.count()
    stats["product_count"] = Product.objects.count()
    stats["chemical_count"] = RawChem.objects.count()
    stats["product_with_puc_count"] = (
        ProductToPUC.objects.values("product_id").distinct().count()
    )
    stats["curated_chemical_count"] = RawChem.objects.filter(
        dsstox__isnull=False
    ).count()
    stats["dsstox_sid_count"] = RawChem.objects.values("dsstox__sid").distinct().count()
    return stats


def index(request):
    stats = get_stats()
    news = News.objects.order_by("-updated_at")[:5]
    return render(
        request, "dashboard/index.html", {"stats": stats, "latest_news": news}
    )


def all_news(request):
    news = News.objects.filter(section="news").order_by("-updated_at")
    return render(request, "news/all_news.html", {"news": news})


def datadocument_count_by_date():
    # Datasets to populate linechart with document-upload statistics
    # Number of datadocuments, both overall and by type, that have been uploaded
    # as of each date
    current_date = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d")
    select_upload_date = {"upload_date": """date(dashboard_datadocument.created_at)"""}
    document_stats = {}
    document_stats["all"] = list(
        DataDocument.objects.extra(select=select_upload_date)
        .values("upload_date")
        .annotate(document_count=Count("id"))
        .order_by("upload_date")
    )
    document_stats_by_type = (
        DataDocument.objects.extra(select=select_upload_date)
        .values("upload_date")
        .annotate(source_type=F("document_type__title"), document_count=Count("id"))
        .order_by("upload_date")
    )
    document_stats["product"] = list(
        document_stats_by_type.filter(source_type="product")
    )
    document_stats["msds_sds"] = list(
        document_stats_by_type.filter(source_type="msds/sds")
    )
    for type in {"all"}:
        document_count = 0
        for item in document_stats[type]:
            if isinstance(item["upload_date"], datetime.date):
                item["upload_date"] = datetime.date.strftime(
                    (item["upload_date"]), "%Y-%m-%d"
                )
            document_count += item["document_count"]
            item["document_count"] = document_count
        # if final record isn't for current date, create one
        for item in document_stats[type][len(document_stats[type]) - 1 :]:
            if item["upload_date"] != current_date:
                document_stats[type].append(
                    {"upload_date": current_date, "document_count": document_count}
                )
    return document_stats


def datadocument_count_by_month():
    # GROUP BY issue solved with https://stackoverflow.com/questions/8746014/django-group-by-date-day-month-year
    chart_start_datetime = datetime.datetime(
        datetime.datetime.now().year - 1, min(12, datetime.datetime.now().month + 1), 1
    )
    document_stats = list(
        DataDocument.objects.filter(created_at__gte=chart_start_datetime)
        .annotate(
            upload_month=(Trunc("created_at", "month", output_field=DateTimeField()))
        )
        .values("upload_month")
        .annotate(document_count=(Count("id")))
        .values("document_count", "upload_month")
        .order_by("upload_month")
    )
    if len(document_stats) < 12:
        for i in range(0, 12):
            chart_month = chart_start_datetime + relativedelta(months=i)
            if (
                i + 1 > len(document_stats)
                or document_stats[i]["upload_month"] != chart_month
            ):
                document_stats.insert(
                    i, {"document_count": "0", "upload_month": chart_month}
                )
    return document_stats


def product_with_puc_count_by_month():
    # GROUP BY issue solved with https://stackoverflow.com/questions/8746014/django-group-by-date-day-month-year
    chart_start_datetime = datetime.datetime(
        datetime.datetime.now().year - 1, min(12, datetime.datetime.now().month + 1), 1
    )
    product_stats = list(
        ProductToPUC.objects.filter(created_at__gte=chart_start_datetime)
        .annotate(
            puc_assigned_month=(Trunc("created_at", "month", output_field=DateField()))
        )
        .values("puc_assigned_month")
        .annotate(product_count=Count("product", distinct=True))
        .order_by("puc_assigned_month")
    )

    if len(product_stats) < 12:
        for i in range(0, 12):
            chart_month = chart_start_datetime + relativedelta(months=i)
            if (
                i + 1 > len(product_stats)
                or product_stats[i]["puc_assigned_month"] != chart_month
            ):
                product_stats.insert(
                    i, {"product_count": "0", "puc_assigned_month": chart_month}
                )
    return product_stats


def download_PUCs(request):
    """This view is used to download all of the PUCs in CSV form.
    """
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="PUCs.csv"'
    pucs = (
        PUC.objects.prefetch_related("cumulative_products_per_puc")
        .order_by("gen_cat", "prod_fam", "prod_type")
        .with_allowed_attributes()
        .with_assumed_attributes()
    )
    writer = csv.writer(response)
    cols = [
        "General category",
        "Product family",
        "Product type",
        "Allowed attributes",
        "Assumed attributes",
        "Description",
        "PUC type",
        "PUC level",
        "Product count",
        "Cumulative product count",
    ]
    writer.writerow(cols)
    for puc in pucs:
        row = [
            puc.gen_cat,
            puc.prod_fam,
            puc.prod_type,
            puc.allowed_attributes,
            puc.assumed_attributes,
            puc.description,
            puc.kind,
            puc.cumulative_products_per_puc.puc_level,
            puc.cumulative_products_per_puc.product_count,
            puc.cumulative_products_per_puc.cumulative_product_count,
        ]
        writer.writerow(row)
    return response


def download_LPKeywords(request):
    """This view gets called to download all of the list presence keywords 
    and their definitions in a csv form.
    """
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="ListPresenceKeywords.csv"'
    writer = csv.writer(response)
    cols = ["Keyword", "Definition", "Kind"]
    writer.writerow(cols)
    LPKeywords = ExtractedListPresenceTag.objects.all()
    for keyword in LPKeywords:
        row = [keyword.name, keyword.definition, keyword.kind]
        writer.writerow(row)

    return response


def download_FunctionalUseCategories(request):
    """This view gets called to download all the functional use categories in a csv form.
    """
    response = HttpResponse(content_type="text/csv")
    response[
        "Content-Disposition"
    ] = 'attachment; filename="FunctionalUseCategories.csv"'
    writer = csv.writer(response)
    cols = ["Title", "Description", "Date Created"]
    writer.writerow(cols)
    categories = FunctionalUseCategory.objects.all()
    for category in categories:
        row = [
            category.title,
            category.description,
            category.created_at.strftime("%m/%d/%Y %H:%M:%S"),
        ]
        writer.writerow(row)

    return response
