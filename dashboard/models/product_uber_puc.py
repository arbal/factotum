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
          select id, product_id, puc_id
          from dashboard_producttopuc
          where (product_id, classification_method) in (
            select product_id,
              case
                when min(uber_order) = 1 then 'MA'
                when min(uber_order) = 2 then 'RU'
                when min(uber_order) = 3 then 'MB'
                when min(uber_order) = 4 then 'BA'
                when min(uber_order) = 5 then 'AU'
                else 'MA'
              end as classification_method
            from
              (select product_id,
                case
                  when classification_method = 'MA' then 1
                  when classification_method = 'RU' then 2
                  when classification_method = 'MB' then 3
                  when classification_method = 'BA' then 4
                  when classification_method = 'AU' then 5
                  else 1
                end as uber_order  
              from dashboard_producttopuc) temp
              group by product_id
              having min(uber_order)
            )
      """

    class Meta:
        managed = False
        db_table = "product_uber_puc"
