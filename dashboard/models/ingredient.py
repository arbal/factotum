from django.db import models
from .common_info import CommonInfo
from django.core.exceptions import ValidationError
from .weight_fraction_type import WeightFractionType
from .extracted_chemical import ExtractedChemical
from .script import Script


def validate_wf_analysis(value):
    if value < 0 or value > 1:
        raise ValidationError(
            (f'Quantity {value} is not allowed'),params={'value': value})


class Ingredient(CommonInfo):
    lower_wf_analysis = models.DecimalField(max_digits=16, decimal_places=15,
                                            null=True, blank=True,
                                            validators=[validate_wf_analysis])
    central_wf_analysis = models.DecimalField(max_digits=16, decimal_places=15,
                                              null=True, blank=True,
                                              validators=[validate_wf_analysis])
    upper_wf_analysis = models.DecimalField(max_digits=16, decimal_places=15,
                                            null=True, blank=True,
                                            validators=[validate_wf_analysis])
    extracted_chemical = models.OneToOneField(to=ExtractedChemical,
                                                    on_delete=models.CASCADE,
                                                    null=True, blank=True)
    script = models.ForeignKey(to=Script, on_delete=models.CASCADE,
                                                    null=True, blank=True)

    def __str__(self):
        return str(self.id)
