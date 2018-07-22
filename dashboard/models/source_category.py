from django.db import models
from .common_info import CommonInfo
from .data_source import DataSource
from django.urls import reverse


class SourceCategory(CommonInfo):
	data_source = models.ForeignKey(DataSource, on_delete=models.CASCADE)
	title = models.CharField(max_length=200, null=False, blank=False)
	source_id = models.CharField(max_length=255, null=True, blank=True)
	source_parent_id = models.CharField(max_length=255, null=True, blank=True)
	path = models.CharField(max_length=255, null=True, blank=True)

	def __str__(self):
		return self.data_source.title + ', ' + self.path

	def get_absolute_url(self):
		return reverse('source_category_edit', kwargs={'pk': self.pk})

	class Meta:
		verbose_name_plural = 'Source categories'
