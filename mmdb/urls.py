from django.urls import path, re_path, include
from django.conf import settings
from django.conf.urls.static import static

import dashboard.views.data_group
import dashboard.views.functional_use_category
from . import views

urlpatterns = [
    path(
        "sample_summary_json/",
        views.MediaSampleSummaryJson.as_view(),
        name="sample_summary_json",
    )
]
if settings.DEBUG is True:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
