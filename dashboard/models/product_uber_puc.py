from django_db_views.db_view import DBView
from django.db import models

from dashboard.models import (
    PUC,
    Product,
    DSSToxLookup,
    ProductToPucClassificationMethod,
)
from dashboard.utils import SimpleTree

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

    classification_method = models.ForeignKey(
        ProductToPucClassificationMethod, on_delete=models.DO_NOTHING
    )
    classification_confidence = models.DecimalField(
        max_digits=6, decimal_places=3, default=1, null=True, blank=True
    )

    def __str__(self):
        return f"{self.product} --> {self.puc}"

    view_definition = """
         SELECT * from dashboard_producttopuc where is_uber_puc = TRUE
      """

    class JSONAPIMeta:
        resource_name = "productToPuc"

    class Meta:
        managed = False
        db_table = "product_uber_puc"


class ProductsPerPuc(DBView):
    puc = CustomOneToOneField(
        PUC,
        on_delete=models.DO_NOTHING,
        related_name="products_per_puc",
        null=True,
        blank=True,
    )
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
    puc = CustomOneToOneField(
        PUC,
        on_delete=models.DO_NOTHING,
        related_name="cumulative_products_per_puc",
        null=True,
        blank=True,
    )
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
    puc = models.ForeignKey(
        PUC, on_delete=models.DO_NOTHING, related_name="products_per_puc_and_sid"
    )
    dsstoxlookup = models.ForeignKey(DSSToxLookup, on_delete=models.DO_NOTHING)
    product_count = models.IntegerField()

    def __str__(self):
        return f"{self.puc} | {self.dsstoxlookup.sid}: {self.product_count} "

    view_definition = """
        SELECT 
                1 AS id,
                ptp.puc_id AS puc_id,
                chem.dsstox_id AS dsstoxlookup_id,
                COUNT(ptp.product_id) AS product_count
            FROM
                (select product_id, puc_id FROM dashboard_producttopuc where dashboard_producttopuc.is_uber_puc = TRUE) ptp
                JOIN dashboard_productdocument ON ptp.product_id = dashboard_productdocument.product_id
                JOIN (select extracted_text_id, dsstox_id from dashboard_rawchem where dsstox_id is not null) chem ON 
                dashboard_productdocument.id = chem.extracted_text_id
            GROUP BY ptp.puc_id , chem.dsstox_id
            """

    class Meta:
        managed = False
        db_table = "products_per_puc_and_sid"


class CumulativeProductsPerPucAndSid(DBView):
    puc = models.ForeignKey(
        PUC,
        on_delete=models.DO_NOTHING,
        related_name="cumulative_products_per_puc_and_sid",
    )
    dsstoxlookup = models.ForeignKey(DSSToxLookup, on_delete=models.DO_NOTHING)
    cumulative_product_count = models.IntegerField()
    product_count = models.IntegerField()
    puc_level = models.IntegerField()
    objects = CumulativeProductsPerPucQuerySet.as_manager()

    def __str__(self):
        return f"{self.puc} | {self.dsstoxlookup.sid}: {self.product_count} "

    view_definition = """
        SELECT cumulative_union .* ,
        COALESCE(products_per_puc_and_sid.product_count,0) as product_count
        FROM
        (SELECT  
        -- gen cat
        1 as id,
        gencat_id.puc_id,
        dsstoxlookup_id, 
        gencat_id.kind_id, 
        sum(products_per_puc_and_sid.product_count) as cumulative_product_count,
        1 as puc_level
        FROM 
        dashboard_puc 
        LEFT JOIN
        products_per_puc_and_sid
        ON products_per_puc_and_sid.puc_id = dashboard_puc.id
        LEFT JOIN (select kind_id, gen_cat, min(id) as puc_id from dashboard_puc where prod_fam = "" and prod_type = "" GROUP BY kind_id, gen_cat) gencat_id
        ON gencat_id.gen_cat = dashboard_puc.gen_cat AND gencat_id.kind_id = dashboard_puc.kind_id
        GROUP BY dsstoxlookup_id, gencat_id.kind_id, gencat_id.gen_cat, gencat_id.puc_id
        HAVING dsstoxlookup_id is not null
        UNION 
        SELECT 
        -- prod fam
        1 as id,
        prodfam_id.puc_id,
        dsstoxlookup_id, 
        prodfam_id.kind_id, 
        sum(products_per_puc_and_sid.product_count) as cumulative_product_count,
        2 as puc_level
        FROM 
        dashboard_puc 
        LEFT JOIN
        products_per_puc_and_sid
        ON products_per_puc_and_sid.puc_id = dashboard_puc.id
        LEFT JOIN (select kind_id, gen_cat, prod_fam, min(id) as puc_id from dashboard_puc where prod_fam <> "" and prod_type = "" GROUP BY kind_id, gen_cat, prod_fam) prodfam_id
        ON prodfam_id.gen_cat = dashboard_puc.gen_cat AND prodfam_id.kind_id = dashboard_puc.kind_id AND prodfam_id.prod_fam = dashboard_puc.prod_fam
        WHERE dashboard_puc.prod_fam <> "" 
        GROUP BY  dsstoxlookup_id, prodfam_id.kind_id, prodfam_id.gen_cat, prodfam_id.puc_id, prodfam_id.prod_fam
        -- exclude gen_cat
        HAVING dsstoxlookup_id is not null
        UNION 
        SELECT 
        -- prod_type
        1 as id,
        puc_id,
        dsstoxlookup_id, 
        kind_id, 
        products_per_puc_and_sid.product_count as cumulative_product_count,
        3 as puc_level
        FROM 
        dashboard_puc 
        LEFT JOIN
        products_per_puc_and_sid
        ON products_per_puc_and_sid.puc_id = dashboard_puc.id
        WHERE dashboard_puc.prod_type <> "" 
        AND dsstoxlookup_id is not null) cumulative_union
        LEFT JOIN
        products_per_puc_and_sid ON
        products_per_puc_and_sid.puc_id = cumulative_union.puc_id
        and products_per_puc_and_sid.dsstoxlookup_id = cumulative_union.dsstoxlookup_id


            """

    class Meta:
        managed = False
        db_table = "cumulative_products_per_puc_and_sid"
