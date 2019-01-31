from django.db import models
from .common_info import CommonInfo
from taggit.models import TagBase
from django.utils.translation import ugettext_lazy as _

class PUCTag(TagBase, CommonInfo):

	class Meta:
		verbose_name = _("PUC Attribute")
		verbose_name_plural = _("PUC Attributes")
		ordering = ('name',)

	def __str__(self):
		return self.name
