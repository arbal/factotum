from django.db import models
from django.db import connection

from .PUC import PUC
from .common_info import CommonInfo
from .product import Product
from django.utils.translation import ugettext_lazy as _

DEFAULT_CLASSIFICATION_METHOD_CODE = "MA"


class ProductToPUC(CommonInfo):

    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    puc = models.ForeignKey(PUC, on_delete=models.CASCADE)
    puc_assigned_usr = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True, blank=True
    )
    puc_assigned_script = models.ForeignKey(
        "Script", on_delete=models.SET_NULL, null=True, blank=True
    )
    classification_method = models.ForeignKey(
        "ProductToPucClassificationMethod",
        max_length=3,
        on_delete=models.PROTECT,
        null=False,
        blank=False,
        default=DEFAULT_CLASSIFICATION_METHOD_CODE,
    )
    classification_confidence = models.DecimalField(
        max_digits=6, decimal_places=3, default=1, null=True, blank=True
    )
    is_uber_puc = models.BooleanField(default=False, db_index=True)

    def __str__(self):
        return f"{self.product} --> {self.puc}"

    def update_uber_puc(self):
        """
        Run the UPDATE query on all the dashboard_producttopuc records 
        that share this one's product_id. 
        """

        uberpuc_update_sql = """
            UPDATE
                dashboard_producttopuc ptp
            LEFT JOIN
                dashboard_producttopucclassificationmethod cm ON cm.id = ptp.classification_method_id
            LEFT JOIN (
                SELECT 
                    ptp.product_id AS product_id,
                    ptp.puc_id AS puc_id,
                    ptp.classification_method_id AS classification_method_id,
                    cm.rank AS rank
                FROM
                    dashboard_producttopuc ptp
                LEFT JOIN dashboard_producttopucclassificationmethod cm ON cm.id = ptp.classification_method_id
            ) ptp_rank ON ptp.product_id = ptp_rank.product_id AND cm.rank > ptp_rank.rank
            SET is_uber_puc = ptp_rank.rank IS NULL
            """
        with connection.cursor() as cursor:
            cursor.execute(
                uberpuc_update_sql + f" WHERE ptp.product_id = {self.product_id}"
            )

    class Meta:
        unique_together = ("product", "puc", "classification_method")


class ProductToPucClassificationMethodManager(models.Manager):
    def get_by_natural_key(self, code):
        return self.get(code=code)


class ProductToPucClassificationMethod(CommonInfo):
    code = models.CharField(
        max_length=3,
        primary_key=True,
        verbose_name="classification method code",
        db_column="id",
    )
    name = models.CharField(
        max_length=100, unique=True, verbose_name="classification method name"
    )
    rank = models.PositiveSmallIntegerField(
        unique=True, verbose_name="classification method rank"
    )

    def natural_key(self):
        return (self.code,)

    def get_by_natural_key(self, code):
        return self.get(code=code)

    objects = ProductToPucClassificationMethodManager()

    class Meta:
        ordering = ["rank"]
        verbose_name = _("PUC classification method")
        verbose_name_plural = _("PUC classification methods")

    def __str__(self):
        return self.code
