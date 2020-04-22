from six import text_type
from taggit.models import TaggedItemBase, TagBase
from taggit.managers import TaggableManager
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _


from .common_info import CommonInfo
from .extracted_text import ExtractedText


class ExtractedHabitsAndPracticesDataType(CommonInfo):
    title = models.CharField(max_length=50, blank=False, null=False)
    description = models.CharField(max_length=255, blank=True)

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
        "dashboard.PUC",
        through="dashboard.ExtractedHabitsAndPracticesToPUC",
        blank=True,
    )
    notes = models.TextField("Notes", blank=True)
    tags = TaggableManager(
        through="dashboard.ExtractedHabitsAndPracticesToTag",
        to="dashboard.ExtractedHabitsAndPracticesTag",
        blank=True,
    )

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


class ExtractedHabitsAndPracticesToTag(TaggedItemBase, CommonInfo):
    """Many-to-many relationship between ExtractedHabitsAndPractices and Tag

    Arguments:
        TaggedItemBase {[type]} -- [description]
        CommonInfo {[type]} -- [description]

    Returns:
        [type] -- [description]
    """

    content_object = models.ForeignKey(
        ExtractedHabitsAndPractices, on_delete=models.CASCADE
    )
    tag = models.ForeignKey(
        "ExtractedHabitsAndPracticesTag",
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s_items",
    )

    class Meta:
        verbose_name = _("Extracted habits and practices to keyword")
        verbose_name_plural = _("Extracted habits and practices to keywords")
        ordering = ("content_object",)

    def __str__(self):
        return str(self.content_object)


class ExtractedHabitsAndPracticesTagKind(CommonInfo):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name = _("Extracted habits and practices keyword kind")
        verbose_name_plural = _("Extracted habits and practices keyword kinds")

    def __str__(self):
        return str(self.name)


class ExtractedHabitsAndPracticesTag(TagBase, CommonInfo):
    definition = models.CharField("Definition", max_length=750, blank=True)
    kind = models.ForeignKey(
        ExtractedHabitsAndPracticesTagKind, default=1, on_delete=models.PROTECT
    )

    class Meta:
        verbose_name = _("Extracted habits and practices keyword")
        verbose_name_plural = _("Extracted habits and practices keywords")
        ordering = ("kind", "name")

    def __str__(self):
        return self.name
