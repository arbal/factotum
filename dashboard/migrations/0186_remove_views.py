# Generated by Django 2.2.17 on 2021-03-30 07:27

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("dashboard", "0185_remove_functionaluse_clean_funcuse")]

    operations = [
        migrations.DeleteModel(name="CumulativeProductsPerPucAndSid"),
        migrations.DeleteModel(name="ProductsPerPucAndSid"),
        migrations.RunSQL(
            sql="DROP VIEW IF EXISTS cumulative_products_per_puc_and_sid",
            reverse_sql="""
            CREATE OR REPLACE VIEW cumulative_products_per_puc_and_sid AS
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
            """,
        ),
        migrations.RunSQL(
            sql="DROP VIEW IF EXISTS products_per_puc_and_sid",
            reverse_sql="""
            CREATE OR REPLACE VIEW products_per_puc_and_sid AS
            SELECT
                1 AS id,
                ptp.puc_id AS puc_id,
                chem.dsstox_id AS dsstoxlookup_id,
                COUNT(ptp.product_id) AS product_count
            FROM
                (select product_id, puc_id FROM dashboard_producttopuc where dashboard_producttopuc.is_uber_puc = TRUE) ptp
                JOIN dashboard_productdocument ON ptp.product_id = dashboard_productdocument.product_id
                JOIN (select extracted_text_id, dsstox_id from dashboard_rawchem where dsstox_id is not null) chem ON
                dashboard_productdocument.document_id = chem.extracted_text_id
            GROUP BY ptp.puc_id , chem.dsstox_id
            """,
        ),
    ]
