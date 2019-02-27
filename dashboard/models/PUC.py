from taggit.managers import TaggableManager

from django.db import models

from .common_info import CommonInfo
from .extracted_habits_and_practices_to_puc import (
                                            ExtractedHabitsAndPracticesToPUC)
from .extracted_habits_and_practices import ExtractedHabitsAndPractices


class PUC(CommonInfo):
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
