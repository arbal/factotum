from taggit.models import TaggedItemBase, TagBase
from taggit.managers import TaggableManager

from django.db import models
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from .common_info import CommonInfo
from .extracted_habits_and_practices_to_puc import (
                                            ExtractedHabitsAndPracticesToPUC)
from .extracted_habits_and_practices import ExtractedHabitsAndPractices


class PUC(CommonInfo):
    KIND_CHOICES = (
        ('UN', 'unknown'),
        ('FO', 'formulations'),
        ('AR', 'articles'),
        ('OC', 'occupational'))

    kind = models.CharField(max_length=2, blank=True, default='UN',
                             choices=KIND_CHOICES)
    gen_cat = models.CharField(max_length=50, blank=False)
    prod_fam = models.CharField(max_length=50, blank=True, default='')
    prod_type = models.CharField(max_length=100, blank=True, default='')
    description = models.TextField(null=False, blank=False)
    last_edited_by = models.ForeignKey('auth.User', on_delete=models.CASCADE,
                                                                    default=1)
    products = models.ManyToManyField('Product', through='ProductToPUC')
    extracted_habits_and_practices = models.ManyToManyField(
                        'dashboard.ExtractedHabitsAndPractices',
                        through='dashboard.ExtractedHabitsAndPracticesToPUC')
    tags = TaggableManager(through='dashboard.PUCToTag',
                           to='dashboard.PUCTag',
                           blank=True,
                           help_text='A set of PUC Attributes applicable to this PUC')

    class Meta:
        ordering = ['gen_cat', 'prod_fam', 'prod_type']
        verbose_name_plural = 'PUCs'

    def __str__(self):
        cats = [self.gen_cat, self.prod_fam, self.prod_type]
        return ' - '.join(cat for cat in cats if cat is not None)

    def natural_key(self):
        return self.gen_cat

    def tag_list(self, obj):
        return u", ".join(o.name for o in obj.tags.all())


    def get_level(self):
        if self.is_level_one:
            return 1
        if self.is_level_two:
            return 2
        else:
            return 3


    @property
    def is_level_one(self): # gen_cat only
        return self.prod_fam is '' and self.prod_type is ''

    @property
    def is_level_two(self): # no prod_type
        return not self.prod_fam is '' and self.prod_type is ''

    @property
    def is_level_three(self): # most granular PUC
        return not self.prod_fam is '' and not self.prod_type is ''

    def get_the_kids(self):
        if self.is_level_one:
            return PUC.objects.filter(gen_cat=self.gen_cat)
        if self.is_level_two:
            return PUC.objects.filter(gen_cat=self.gen_cat,
                                        prod_fam=self.prod_fam)
        if self.is_level_three:
            return PUC.objects.filter(pk=self.pk)

    @property
    def product_count(self):
        '''Don't use this in large querysets. It uses a SQL query for each 
        PUC record. '''
        return self.products.count()

    @property
    def admin_url(self):
        return reverse('admin:dashboard_puc_change', args=(self.pk,))
        
    def get_assumed_tags(self):
        '''Queryset of used to filter which PUCs a Product can have '''
        qs = PUCToTag.objects.filter(content_object=self, assumed=True)
        return PUCTag.objects.filter(dashboard_puctotag_items__in=qs)


class PUCToTag(TaggedItemBase, CommonInfo):
    content_object = models.ForeignKey(PUC, on_delete=models.CASCADE)
    tag = models.ForeignKey('PUCTag', on_delete=models.CASCADE,
                            related_name="%(app_label)s_%(class)s_items")
    assumed = models.BooleanField(default=False)

    def __str__(self):
        return str(self.content_object)


class PUCTag(TagBase, CommonInfo):

    class Meta:
        verbose_name = _("PUC Attribute")
        verbose_name_plural = _("PUC Attributes")
        ordering = ('name',)

    def __str__(self):
        return self.name
