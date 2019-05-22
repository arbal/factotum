from taggit.models import TaggedItemBase, TagBase
from taggit.managers import TaggableManager
from django.utils.translation import ugettext_lazy as _

from django.db import models
from .common_info import CommonInfo
from .raw_chem import RawChem


class ExtractedListPresence(CommonInfo, RawChem):

    qa_flag = models.BooleanField(default=False)
    tags = TaggableManager(through='dashboard.ExtractedListPresenceToTag',
                           to='dashboard.ExtractedListPresenceTag',
                           blank=True,
                           help_text='A set of keywords applicable to this Extracted List Presence')

    tags = TaggableManager(through='dashboard.ExtractedListPresenceToTag',
                           to='dashboard.ExtractedListPresenceTag',
                           blank=True)

    @classmethod
    def detail_fields(cls):
        return ['raw_cas','raw_chem_name']

    def __str__(self):
        return str(self.raw_chem_name) if self.raw_chem_name else ''

    def get_datadocument_url(self):
        return self.extracted_cpcat.data_document.get_absolute_url()

    def get_extractedtext(self):
        return self.extracted_cpcat.extractedtext_ptr
    
    @property
    def data_document(self):
        return self.extracted_text.data_document


class ExtractedListPresenceToTag(TaggedItemBase, CommonInfo):
    content_object = models.ForeignKey(ExtractedListPresence, on_delete=models.CASCADE)
    tag = models.ForeignKey('ExtractedListPresenceTag', on_delete=models.CASCADE,
                            related_name="%(app_label)s_%(class)s_items")


    class Meta:
        verbose_name = _("Extracted list presence to keyword")
        verbose_name_plural = _("Extracted list presence to keywords")
        ordering = ('content_object',)


    def __str__(self):
        return str(self.content_object)


class ExtractedListPresenceTag(TagBase, CommonInfo):

    definition = models.CharField("Definition", max_length=255,
                                        null=True, blank=True)

    class Meta:

        verbose_name = _("Extracted list presence keyword")
        verbose_name_plural = _("Extracted list presence keywords")
        ordering = ('name',)

    def __str__(self):
        return self.name
