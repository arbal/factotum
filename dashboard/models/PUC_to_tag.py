from django.db import models
from .common_info import CommonInfo
from .PUC import PUC
from .PUC_tag import PUCTag
from taggit.models import TaggedItemBase

class PUCToTag(TaggedItemBase, CommonInfo):
	content_object = models.ForeignKey(PUC, on_delete=models.CASCADE)
	tag = models.ForeignKey(PUCTag, on_delete=models.CASCADE,
							related_name="%(app_label)s_%(class)s_items")

	def __str__(self):
		return str(self.id)

