from django_db_views.db_view import DBView
from django.db import models

from dashboard.models import PUC, Product
from dashboard.models.custom_onetoone_field import CustomOneToOneField


class ProductUberPuc(DBView):
    product = CustomOneToOneField(
        Product,
        on_delete=models.DO_NOTHING,
        related_name="product_uber_puc",
        null=True,
        blank=True,
    )
    puc = models.ForeignKey(PUC, on_delete=models.DO_NOTHING)

    def __str__(self):
        return f"{self.product} --> {self.puc}"

    view_definition = """
        SELECT ptp.*
        FROM (
            SELECT ptp.id, product_id, puc_id, classification_method_id, rank
            FROM dashboard_producttopuc ptp
            LEFT JOIN dashboard_producttopucclassificationmethod cm ON cm.id = ptp.classification_method_id
        ) ptp
        LEFT JOIN (
            SELECT product_id, puc_id, classification_method_id, rank
            FROM dashboard_producttopuc ptp
            LEFT JOIN dashboard_producttopucclassificationmethod cm ON cm.id = ptp.classification_method_id 
        ) ptp_rank ON ptp.product_id = ptp_rank.product_id AND ptp.rank > ptp_rank.rank
        WHERE ptp_rank.rank IS NULL
      """

    class Meta:
        managed = False
        db_table = "product_uber_puc"
