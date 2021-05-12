from django.db import models
from django.utils.text import Truncator

from dashboard.models.common_info import CommonInfo


class Comment(CommonInfo):
    email = models.EmailField(max_length=100)
    subject = models.CharField(max_length=100)
    body = models.CharField(max_length=500)
    page_url = models.URLField(blank=True)

    def __str__(self):
        return str(self.email) + ": " + Truncator(self.body).chars(100)
