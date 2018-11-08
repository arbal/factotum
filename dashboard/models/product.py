from django.db import models
from .common_info import CommonInfo
from .data_source import DataSource
from .source_category import SourceCategory
from django.urls import reverse
from taggit.managers import TaggableManager

class Product(CommonInfo):
    data_source = models.ForeignKey(DataSource, related_name='source',
                                    on_delete=models.CASCADE)
    documents = models.ManyToManyField(through='dashboard.ProductDocument',
                                       to='dashboard.DataDocument')
    tags = TaggableManager(through='dashboard.ProductToTag',
                           to='dashboard.PUCTag',
                           help_text=('A set of PUC Tags applicable '
                                                            'to this Product'))
    source_category = models.ForeignKey(SourceCategory,
                                                on_delete=models.CASCADE,
                                                null=True, blank=True)
    title = models.CharField(max_length=255)
    manufacturer = models.CharField(db_index=True, max_length=250,
                            null=True, blank=True, default = '')
    upc = models.CharField(db_index=True, max_length=60, null=False,
                            blank=False, unique=True)
    url = models.CharField(max_length=500, null=True, blank=True)
    brand_name = models.CharField(db_index=True, max_length=200, null=True,
                            blank=True, default = '')
    size = models.CharField(max_length=100, null=True, blank=True)
    model_number = models.CharField(max_length=200, null=True, blank=True)
    color = models.CharField(max_length=100, null=True, blank=True)
    item_id = models.IntegerField(null=True, blank=True)
    parent_item_id = models.IntegerField(null=True, blank=True)
    short_description = models.TextField(null=True, blank=True)
    long_description = models.TextField(null=True, blank=True)
    thumb_image = models.CharField(max_length=500, null=True, blank=True)
    medium_image = models.CharField(max_length=500, null=True, blank=True)
    large_image = models.CharField(max_length=500, null=True, blank=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('product_detail', kwargs={'pk': self.pk})

    def get_uber_product_to_puc(self):
        pucs = self.producttopuc_set
        if pucs.filter(classification_method='MA').exists():
            return pucs.filter(classification_method='MA').first()
        elif pucs.filter(classification_method='MB').exists():
            return pucs.filter(classification_method='MB').first()
        elif pucs.filter(classification_method='RU').exists():
            return pucs.filter(classification_method='RU').first()
        elif pucs.filter(classification_method='AU').exists():
            return pucs.filter(classification_method='AU').first()
        else:
            return None

    def get_uber_puc(self):
        thispuc = self.get_uber_product_to_puc()
        if thispuc is not None:
            return thispuc.PUC
        else:
            return None

    def get_tag_list(self):
        return u", ".join(o.name for o in self.tags.all())

    # returns list of valid puc_tags
    def get_puc_tag_list(self):
        all_uber_tags = self.get_uber_product_to_puc().PUC.tags.all()
        return u", ".join(o.name for o in all_uber_tags)

    # returns set of valid puc_tags
    def get_puc_tags(self):
        return self.get_uber_product_to_puc().PUC.tags.all()

    class Meta:
          ordering = ['-created_at']
