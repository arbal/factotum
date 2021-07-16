from django.db import models
from .common_info import CommonInfo
from ckeditor.fields import RichTextField


class News(CommonInfo):
    subject = models.CharField(max_length=200)
    body = RichTextField()
    section = models.CharField(max_length=20, default="news")

    def __str__(self):
        return self.subject

    class Meta:
        verbose_name_plural = "News"
