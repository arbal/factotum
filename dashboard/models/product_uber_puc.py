from django_db_views.db_view import DBView
from django.db import models

from dashboard.models import PUC, Product, DSSToxLookup
from dashboard.utils import GroupConcat, SimpleTree
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


class ProductsPerPuc(DBView):
    puc = models.ForeignKey(PUC, on_delete=models.DO_NOTHING)
    product_count = models.IntegerField()

    def __str__(self):
        return f"{self.puc}: {self.product_count} "

    view_definition = """
         select dashboard_puc.id as id, dashboard_puc.id as puc_id, kind_id, code, gen_cat, prod_fam, prod_type , coalesce(product_count , 0) as product_count
            from dashboard_puc 
            left join 
            (select puc_id, count(product_id) as product_count from product_uber_puc group by puc_id) uberpucs 
            on uberpucs.puc_id = dashboard_puc.id
            left join dashboard_puckind on kind_id = dashboard_puckind.id
            ;
            """

    class Meta:
        managed = False
        db_table = "products_per_puc"


class CumulativeProductsPerPucQuerySet(models.QuerySet):
    def astree(self, include=None):
        """ Returns a SimpleTree representation of the CumulativeProductsPerPuc queryset.
        """
        tree = SimpleTree()
        for p in self:
            names = tuple(
                n for n in (p.puc.gen_cat, p.puc.prod_fam, p.puc.prod_type) if n
            )
            tree[names] = p
            # tree[names] = {
            #     "puc_id":p.puc.id,
            #     "kind":p.puc.kind.code,
            #     "gen_cat":p.puc.gen_cat,
            #     "prod_fam":p.puc.prod_fam,
            #     "prod_type":p.puc.prod_type,
            #     "product_count":p.product_count,
            #     "cumulative_product_count":p.cumulative_product_count
            #     }
        return tree

    def flatdictastree(self, include=None):
        """ Returns a SimpleTree representation of the version 
        of the queryset used in the bubble plots, that's been flattened 
        to remove the instance__puc relationship.

        This approach of using two different methods depending on the 
        format of the PUC records contrasts with the approach taken in 
        PUCQuerySet, which uses `if isinstance(puc, ...):` to test whether
        the incoming data is a PUC object or a dict.
            
        """
        tree = SimpleTree()
        for p in self:
            names = tuple(n for n in (p["gen_cat"], p["prod_fam"], p["prod_type"]) if n)
            tree[names] = p
        return tree


class CumulativeProductsPerPuc(DBView):
    puc = models.ForeignKey(PUC, on_delete=models.DO_NOTHING)
    product_count = models.IntegerField()
    cumulative_product_count = models.IntegerField()
    puc_level = models.IntegerField()
    objects = CumulativeProductsPerPucQuerySet.as_manager()

    def __str__(self):
        return f"{self.puc}: {self.cumulative_product_count} "

    view_definition = """
        SELECT 
            products_per_puc.id,
            products_per_puc.puc_id,
            products_per_puc.product_count,
            prod_fams.prod_fam_count,
            gen_cats.gen_cat_count,
            -- cumulative counts
            CASE
                -- a prod_fam record
                WHEN (products_per_puc.prod_type IS NULL OR products_per_puc.prod_type = "") 
                    AND 
                    (products_per_puc.prod_fam IS NOT NULL AND products_per_puc.prod_fam <> "")
                THEN prod_fam_count
                -- a gen_cat record
                WHEN (products_per_puc.prod_fam IS NULL OR products_per_puc.prod_fam = "") 
                THEN gen_cat_count
                -- a prod_type record
                ELSE product_count
            END as cumulative_product_count,
            CASE
                -- a prod_fam record
                WHEN (products_per_puc.prod_type IS NULL OR products_per_puc.prod_type = "") 
                    AND 
                    (products_per_puc.prod_fam IS NOT NULL AND products_per_puc.prod_fam <> "")
                THEN 2
                -- a gen_cat record
                WHEN (products_per_puc.prod_fam IS NULL OR products_per_puc.prod_fam = "") 
                THEN 1
                -- a prod_type record
                ELSE 3
            END as puc_level
        FROM
            products_per_puc
        LEFT JOIN
            (SELECT 
                kind_id, gen_cat, SUM(product_count) gen_cat_count
            FROM
                products_per_puc
            GROUP BY kind_id, gen_cat) gen_cats 
            ON gen_cats.kind_id = products_per_puc.kind_id AND gen_cats.gen_cat = products_per_puc.gen_cat
        LEFT JOIN
            (SELECT 
                kind_id, gen_cat, prod_fam, SUM(product_count) prod_fam_count
            FROM
                products_per_puc
            WHERE
                prod_fam IS NOT NULL AND products_per_puc.prod_fam <> ""
            GROUP BY kind_id, gen_cat, prod_fam) prod_fams 
            ON 
            prod_fams.kind_id = products_per_puc.kind_id AND 
            prod_fams.gen_cat = products_per_puc.gen_cat AND 
            prod_fams.prod_fam = products_per_puc.prod_fam AND products_per_puc.prod_fam <> ""
        ;
            """

    class Meta:
        managed = False
        db_table = "cumulative_products_per_puc"

class ProductsPerPucAndSid(DBView):
    puc = models.ForeignKey(PUC, on_delete=models.DO_NOTHING)
    sid = models.ForeignKey(DSSToxLookup, on_delete=models.DO_NOTHING)
    product_count = models.IntegerField()

    def __str__(self):
        return f"{self.puc} | {self.sid}: {self.product_count} "

    view_definition = """
        SELECT 
            product_uber_puc.puc_id AS puc_id,
            dashboard_dsstoxlookup.sid as dsstoxlookup_id ,
            count(product_uber_puc.product_id) AS product_count
        FROM
            product_uber_puc
            INNER JOIN
            dashboard_productdocument ON (product_uber_puc.product_id = dashboard_productdocument.product_id)
                INNER JOIN
            dashboard_datadocument ON (dashboard_productdocument.document_id = dashboard_datadocument.id)
                INNER JOIN
            dashboard_rawchem ON (dashboard_datadocument.id = dashboard_rawchem.extracted_text_id)
                INNER JOIN
            dashboard_dsstoxlookup ON (dashboard_rawchem.dsstox_id = dashboard_dsstoxlookup.id)
            GROUP BY product_uber_puc.puc_id, sid
            ;
            """

    class Meta:
        managed = False
        db_table = "products_per_puc_and_sid"