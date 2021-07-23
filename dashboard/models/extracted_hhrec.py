from django.db import models
from six import text_type

from .extracted_text import ExtractedText
from .raw_chem import RawChem


class ExtractedHHRec(RawChem):
    """
    This is the chemical-level detail model for human health data. 
    Its parent records use the `dashboard.models.extracted_hhdoc.ExtractedHHDoc` model.
    """

    medium = models.CharField("Medium", max_length=30, blank=True)
    sampling_method = models.TextField("Sampling Method", blank=True)
    analytical_method = models.TextField("Analytical Method", blank=True)
    num_measure = models.TextField("Numeric Measure", null=True, blank=True)
    num_nondetect = models.TextField("Numeric Nondetect", null=True, blank=True)

    class JSONAPIMeta:
        resource_name = "humanHealthRecord"

    @classmethod
    def detail_fields(cls):
        """Lists the fields to be displayed on a detail form

        Returns:
            list -- a list of field names
        """
        return [
            "raw_chem_name",
            "raw_cas",
            "medium",
            "num_measure",
            "num_nondetect",
            "sampling_method",
            "analytical_method",
        ]

    @classmethod
    def auditlog_fields(cls):
        """Lists the fields to be included in the audit log triggers

        Returns:
            list -- a list of field names
        """
        return [
            "medium",
            "sampling_method",
            "analytical_method",
            "num_measure",
            "num_nondetect",
        ]

    def get_datadocument_url(self):
        return self.extractedtext_ptr.data_document.get_absolute_url()

    @property
    def data_document(self):
        return self.extractedtext_ptr.data_document

    @property
    def extracted_hhdoc(self):
        return ExtractedText.objects.get_subclass(
            pk=self.extracted_text.data_document_id
        )

    def __get_label(self, field):
        return text_type(self._meta.get_field(field).verbose_name)

    @property
    def medium_label(self):
        return self.__get_label("medium")

    @property
    def sampling_method_label(self):
        return self.__get_label("sampling_method")

    @property
    def analytical_method_label(self):
        return self.__get_label("analytical_method")

    @property
    def num_measure_label(self):
        return self.__get_label("num_measure")

    @property
    def num_nondetect_label(self):
        return self.__get_label("num_nondetect")
