from django.db import models
from .common_info import CommonInfo
from .product import Product
from .product_category import ProductCategory


class ProductToPUC(CommonInfo):
    MANUAL = 'MA'
    AUTOMATIC = 'AU'
    CLASSIFICATION_CHOICES = (
        (MANUAL, 'Manual'),
        (AUTOMATIC, 'Automatic'))

    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    PUC = models.ForeignKey(ProductCategory, on_delete=models.CASCADE)
    puc_assigned_usr = models.ForeignKey('auth.User',
                                         on_delete=models.SET_NULL, null=True, blank=True)
    puc_assigned_script = models.ForeignKey('Script',
                                            on_delete=models.SET_NULL, null=True, blank=True)
    puc_assigned_time = models.DateTimeField(null=True, blank=True)
    classification_method = models.CharField(max_length=2, choices=CLASSIFICATION_CHOICES, null=False, default='AU')
    classification_confidence = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)

    def __str__(self):
        return self.id

