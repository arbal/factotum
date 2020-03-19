from six import text_type

from django.db import models
from django.core.exceptions import ValidationError

from .common_info import CommonInfo
from .extracted_text import ExtractedText


class ExtractedHabitsAndPracticesDataType(CommonInfo):
    title = models.CharField(max_length=50, blank=False, null=False)
    description = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.title


class ExtractedHabitsAndPractices(CommonInfo):
    extracted_text = models.ForeignKey(
        ExtractedText, on_delete=models.CASCADE, related_name="practices"
    )
    data_type = models.ForeignKey(
        ExtractedHabitsAndPracticesDataType, on_delete=models.PROTECT
    )
    product_surveyed = models.CharField("Product Surveyed", max_length=50)
    PUCs = models.ManyToManyField(
        "dashboard.PUC", through="dashboard.ExtractedHabitsAndPracticesToPUC"
    )
    notes = models.TextField("Notes", blank=True)

    def __str__(self):
        return self.product_surveyed

    @classmethod
    def detail_fields(cls):
        return ["product_surveyed", "data_type", "notes"]

    def get_extractedtext(self):
        return self.extracted_text

    @property
    def data_document(self):
        return self.extracted_text.data_document

    def __get_label(self, field):
        return text_type(self._meta.get_field(field).verbose_name)

    @property
    def product_surveyed_label(self):
        return self.__get_label("product_surveyed")

    @property
    def notes_label(self):
        return self.__get_label("notes")
