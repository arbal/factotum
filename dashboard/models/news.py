from django.db import models
from .common_info import CommonInfo
from ckeditor_uploader.fields import RichTextUploadingField


class News(CommonInfo):
    GETTING_STARTED_SECTION_NAME = "gettingstarted"
    SECTION_CHOICES = (
        ("news", "news"),
        (GETTING_STARTED_SECTION_NAME, "getting started"),
    )
    subject = models.CharField(max_length=200)
    body = RichTextUploadingField()
    section = models.CharField(max_length=20, choices=SECTION_CHOICES, default="news")

    def __str__(self):
        return self.subject

    class Meta:
        verbose_name_plural = "News"
