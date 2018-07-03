from django.db import models
from .common_info import CommonInfo
from django.core.exceptions import ValidationError
from .weight_fraction_type import WeightFractionType

def validate_wf_analysis(value):
	if value < 0 or value > 1:
		raise ValidationError(
			('Quantity {} is not allowed'.format(value)),params={'value': value},
		)


class Ingredient(CommonInfo):
	products = models.ManyToManyField(through='dashboard.ProductToIngredient',
									  to='dashboard.Product')
	dsstox_substances = models.ManyToManyField(through='dashboard.DSSToxSubstanceToIngredient',
											   to='dashboard.DSSToxSubstance')
	lower_wf_analysis = models.DecimalField(max_digits=16, decimal_places=15,
											null=True, blank=True, validators=[validate_wf_analysis])
	central_wf_analysis = models.DecimalField(max_digits=16, decimal_places=15,
											  null=True, blank=True, validators=[validate_wf_analysis])
	upper_wf_analysis = models.DecimalField(max_digits=16, decimal_places=15,
											null=True, blank=True, validators=[validate_wf_analysis])
	weight_fraction_type = models.ForeignKey(WeightFractionType, on_delete=models.PROTECT, null=True, default='1')

	def __str__(self):
		return str(self.id)
