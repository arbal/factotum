from taggit.models import TaggedItemBase, TagBase
from taggit.managers import TaggableManager
from django.utils.translation import ugettext_lazy as _

from django.db import models
from .common_info import CommonInfo
from .raw_chem import RawChem


class ExtractedListPresence(CommonInfo, RawChem):
    raw_cas_old = models.CharField("Raw CAS", max_length=100,
                                        null=True, blank=True)
    raw_chem_name_old = models.CharField("Raw chemical name", max_length=500,
                                        null=True, blank=True)
    qa_flag = models.BooleanField(default=False)
    tags = TaggableManager(through='dashboard.ExtractedListPresenceToTag',
                           to='dashboard.ExtractedListPresenceTag',
                           blank=True,
                           help_text='A set of keywords applicable to this Extracted List Presence')

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

    def __str__(self):
        return str(self.content_object)


class ExtractedListPresenceTag(TagBase, CommonInfo):

    class Meta:
        verbose_name = _("ExtractedListPresence Keyword")
        verbose_name_plural = _("ExtractedListPresence Keywords")
        ordering = ('name',)

    def __str__(self):
        return self.name
