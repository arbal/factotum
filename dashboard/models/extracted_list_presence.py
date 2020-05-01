from django.db import models
from django.utils.translation import ugettext_lazy as _
from six import text_type
from taggit.managers import TaggableManager
from taggit.models import TaggedItemBase, TagBase

from .common_info import CommonInfo
from .raw_chem import RawChem


class ExtractedListPresence(RawChem):
    """
    A record of a chemical's presence in a CPCat list

    :param qa_flag: whether a record has been QA approved
    :param report_funcuse: the reported functional use of a list record
    """

    qa_flag = models.BooleanField(default=False)
    tags = TaggableManager(
        through="dashboard.ExtractedListPresenceToTag",
        to="dashboard.ExtractedListPresenceTag",
        blank=True,
    )

    @classmethod
    def detail_fields(cls):
        """Lists the fields to be displayed on a detail form

        Returns:
            list -- a list of field names
        """
        return ["raw_cas", "raw_chem_name", "component"]

    def get_datadocument_url(self):
        """Traverses the relationship to the DataDocument model

        Returns:
            URL
        """
        return self.extracted_text.data_document.get_absolute_url()

    def get_extractedtext(self):
        return self.extracted_text

    @property
    def data_document(self):
        return self.extracted_text.data_document

    def __get_label(self, field):
        return text_type(self._meta.get_field(field).verbose_name)

    @property
    def report_funcuse_label(self):
        return self.__get_label("report_funcuse")

    @classmethod
    def auditlog_fields(cls):
        """Needed, else inherited method from RawChem will apply with wrong fields"""
        return None


class ExtractedListPresenceToTag(TaggedItemBase, CommonInfo):
    """Many-to-many relationship between ExtractedListPresence and Tag

    Arguments:
        TaggedItemBase {[type]} -- [description]
        CommonInfo {[type]} -- [description]

    Returns:
        [type] -- [description]
    """

    content_object = models.ForeignKey(ExtractedListPresence, on_delete=models.CASCADE)
    tag = models.ForeignKey(
        "ExtractedListPresenceTag",
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s_items",
    )

    class Meta:
        unique_together = ["content_object", "tag"]
        verbose_name = _("Extracted list presence to keyword")
        verbose_name_plural = _("Extracted list presence to keywords")
        ordering = ("content_object",)

    def __str__(self):
        return str(self.content_object)


class ExtractedListPresenceTagKind(CommonInfo):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name = _("Extracted list presence keyword kind")
        verbose_name_plural = _("Extracted list presence keyword kinds")

    def __str__(self):
        return str(self.name)


class ExtractedListPresenceTag(TagBase, CommonInfo):
    definition = models.CharField("Definition", max_length=750, blank=True)
    kind = models.ForeignKey(
        ExtractedListPresenceTagKind, default=1, on_delete=models.PROTECT
    )

    class Meta:
        verbose_name = _("Extracted list presence keyword")
        verbose_name_plural = _("Extracted list presence keywords")
        ordering = ("name",)

    def __str__(self):
        return self.name
