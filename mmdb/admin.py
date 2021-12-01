from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from mmdb.models import MediaSampleSummary


class MediaSampleSummaryAdmin(admin.ModelAdmin):
    list_display = ("__str__",)


admin.site.register(MediaSampleSummary)
