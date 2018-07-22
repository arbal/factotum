import os
import shutil

from django.db import models
from .common_info import CommonInfo
from django.urls import reverse
from django.dispatch import receiver
from .group_type import GroupType


# could be used for dynamically creating filename on instantiation
# in the 'upload_to' param on th FileField
def update_filename(instance, filename):
    name_fill_space = instance.name.replace(' ', '_')
    name = '{0}/{0}_{1}'.format(name_fill_space, filename) # potential space errors in name
    return name


class DataGroup(CommonInfo):

    name = models.CharField(max_length=50)
    description = models.TextField(null=True, blank=True)
    downloaded_by = models.ForeignKey('auth.User', on_delete=models.SET_DEFAULT, default = 1)
    downloaded_at = models.DateTimeField()
    download_script = models.ForeignKey('Script', on_delete=models.SET_NULL, default=None, null=True, blank=True)
    data_source = models.ForeignKey('DataSource', on_delete=models.CASCADE)
    csv = models.FileField(upload_to=update_filename, null=True)
    zip_file = models.CharField(max_length=100)
    group_type = models.ForeignKey(GroupType, on_delete=models.SET_DEFAULT, default=1, null=True, blank=True)


    def matched_docs(self):
        return self.datadocument_set.filter(matched=True).count()

    def all_matched(self):
        return all(self.datadocument_set.values_list('matched', flat=True))

    def all_extracted(self):
        return all(self.datadocument_set.values_list('extracted', flat=True))

    def registered_docs(self):
        return self.datadocument_set.count()

    def extracted_docs(self):
        return self.datadocument_set.filter(extracted=True).count()

    def __str__(self):
        return self.name

    def dgurl(self):
        return self.name.replace(' ', '_')

    def get_absolute_url(self):
        return reverse('data_group_edit', kwargs={'pk': self.pk})


@receiver(models.signals.post_delete, sender=DataGroup)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    Deletes datagroup directory from filesystem
    when datagroup instance is deleted.
    """
    dg_folder = os.path.split(instance.csv.path)[0]
    if os.path.isdir(dg_folder):
        shutil.rmtree(dg_folder)
