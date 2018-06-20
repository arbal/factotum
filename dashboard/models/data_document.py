from django.db import models
from .common_info import CommonInfo
from django.core.urlresolvers import reverse
from django.utils import timezone
from .document_type import DocumentType


class DataDocument(CommonInfo):

    filename = models.CharField(max_length=100)
    title = models.CharField(max_length=255)
    url = models.CharField(null=True, blank=True, max_length=200)
    product_category = models.CharField(null=True, blank=True, max_length=50)
    data_group = models.ForeignKey('DataGroup', on_delete=models.CASCADE)
    products = models.ManyToManyField('Product', through='ProductDocument')
    matched = models.BooleanField(default=False)
    extracted = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(default=timezone.now)
    document_type = models.ForeignKey(DocumentType, on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return str(self.title)

    def get_absolute_url(self):
        return reverse('data_document', kwargs={'pk': self.pk})

    def get_download_script(self):
        return self__data_group.download_script

    def indexing(self):
        obj = DataDocumentIndex(
            meta={'id': self.id},
            title=self.title,
            filename=self.filename,
            url=self.url,
            facet_model_name='Data Document',
        )
        obj.save()
        return obj.to_dict(include_meta=True)
