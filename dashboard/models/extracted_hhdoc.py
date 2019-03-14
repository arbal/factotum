from django.db import models
from django.utils.translation import ugettext_lazy as _

from .extracted_text import ExtractedText

class ExtractedHHDoc(ExtractedText):

    GENDER_CHOICES = (
        ('BO', 'Both'),
        ('FM', 'Female'),
        ('MA', 'Male')
    )    
    
    hhe_report_number = models.CharField("HHE Report Number", max_length=30,
                                        null=False, blank=False)
    study_location = models.CharField("Study Location", max_length=50,
                                        null=True, blank=True)
    naics_code = models.CharField("NAICS Code", max_length=10,
                                        null=True, blank=True)
    sampling_date = models.CharField("Date of Sampling", max_length=75,
                                        null=True, blank=True)
    population_gender = models.CharField("Gender of Population",max_length=2,
                                        choices=GENDER_CHOICES,
                                        null=True, blank=True)  
    population_age = models.CharField("Age of Population", max_length=75,
                                        null=True, blank=True)
    population_other = models.CharField("Other Description of Population", max_length=255,
                                        null=True, blank=True)
    occupation = models.CharField("Occupation", max_length=75,
                                        null=True, blank=True)
    facility = models.CharField("Facility", max_length=75,
                                        null=True, blank=True)

    def __str__(self):
        return str(self.data_document)
    

