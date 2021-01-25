# Generated by Django 2.2.17 on 2021-01-11 23:42

from django.db import migrations
import django_db_views.migration_functions
import django_db_views.operations


class Migration(migrations.Migration):

    dependencies = [("dashboard", "0180_products_per_puc")]

    operations = [
        django_db_views.operations.ViewRunPython(
            code=django_db_views.migration_functions.ForwardViewMigration(
                "SELECT ptp.*\n         FROM (\n             SELECT ptp.id, product_id, puc_id, classification_method_id, rank\n             FROM dashboard_producttopuc ptp\n             LEFT JOIN dashboard_producttopucclassificationmethod cm ON cm.id = ptp.classification_method_id\n         ) ptp\n         LEFT JOIN (\n             SELECT product_id, puc_id, classification_method_id, rank\n             FROM dashboard_producttopuc ptp\n             LEFT JOIN dashboard_producttopucclassificationmethod cm ON cm.id = ptp.classification_method_id \n         ) ptp_rank ON ptp.product_id = ptp_rank.product_id AND ptp.rank > ptp_rank.rank\n         WHERE ptp_rank.rank IS NULL",
                "product_uber_puc",
            ),
            reverse_code=django_db_views.migration_functions.BackwardViewMigration(
                "select id, product_id, puc_id\n          from dashboard_producttopuc\n          where (product_id, classification_method) in (\n            select product_id,\n              case\n                when min(uber_order) = 1 then 'MA'\n                when min(uber_order) = 2 then 'RU'\n                when min(uber_order) = 3 then 'MB'\n                when min(uber_order) = 4 then 'BA'\n                when min(uber_order) = 5 then 'AU'\n                else 'MA'\n              end as classification_method\n            from\n              (select product_id,\n                case\n                  when classification_method = 'MA' then 1\n                  when classification_method = 'RU' then 2\n                  when classification_method = 'MB' then 3\n                  when classification_method = 'BA' then 4\n                  when classification_method = 'AU' then 5\n                  else 1\n                end as uber_order  \n              from dashboard_producttopuc) temp\n              group by product_id\n              having min(uber_order)\n            )",
                "product_uber_puc",
            ),
            atomic=False,
        ),
        django_db_views.operations.ViewRunPython(
            code=django_db_views.migration_functions.ForwardViewMigration(
                "select dashboard_puc.id as id, dashboard_puc.id as puc_id, kind_id, code, gen_cat, prod_fam, prod_type , coalesce(product_count , 0) as product_count\n            from dashboard_puc \n            left join \n            (select puc_id, count(product_id) as product_count from product_uber_puc group by puc_id) uberpucs \n            on uberpucs.puc_id = dashboard_puc.id\n            left join dashboard_puckind on kind_id = dashboard_puckind.id\n            ",
                "products_per_puc",
            ),
            reverse_code=django_db_views.migration_functions.BackwardViewMigration(
                "", "products_per_puc"
            ),
            atomic=False,
        ),
        django_db_views.operations.ViewRunPython(
            code=django_db_views.migration_functions.ForwardViewMigration(
                'SELECT \n            products_per_puc.id,\n            products_per_puc.puc_id,\n            products_per_puc.product_count,\n            prod_fams.prod_fam_count,\n            gen_cats.gen_cat_count,\n            -- cumulative counts\n            CASE\n                -- a prod_fam record\n                WHEN (products_per_puc.prod_type IS NULL OR products_per_puc.prod_type = "") \n                    AND \n                    (products_per_puc.prod_fam IS NOT NULL AND products_per_puc.prod_fam <> "")\n                THEN prod_fam_count\n                -- a gen_cat record\n                WHEN (products_per_puc.prod_fam IS NULL OR products_per_puc.prod_fam = "") \n                THEN gen_cat_count\n                -- a prod_type record\n                ELSE product_count\n            END as cumulative_product_count,\n            CASE\n                -- a prod_fam record\n                WHEN (products_per_puc.prod_type IS NULL OR products_per_puc.prod_type = "") \n                    AND \n                    (products_per_puc.prod_fam IS NOT NULL AND products_per_puc.prod_fam <> "")\n                THEN 2\n                -- a gen_cat record\n                WHEN (products_per_puc.prod_fam IS NULL OR products_per_puc.prod_fam = "") \n                THEN 1\n                -- a prod_type record\n                ELSE 3\n            END as puc_level\n        FROM\n            products_per_puc\n        LEFT JOIN\n            (SELECT \n                kind_id, gen_cat, SUM(product_count) gen_cat_count\n            FROM\n                products_per_puc\n            GROUP BY kind_id, gen_cat) gen_cats \n            ON gen_cats.kind_id = products_per_puc.kind_id AND gen_cats.gen_cat = products_per_puc.gen_cat\n        LEFT JOIN\n            (SELECT \n                kind_id, gen_cat, prod_fam, SUM(product_count) prod_fam_count\n            FROM\n                products_per_puc\n            WHERE\n                prod_fam IS NOT NULL AND products_per_puc.prod_fam <> ""\n            GROUP BY kind_id, gen_cat, prod_fam) prod_fams \n            ON \n            prod_fams.kind_id = products_per_puc.kind_id AND \n            prod_fams.gen_cat = products_per_puc.gen_cat AND \n            prod_fams.prod_fam = products_per_puc.prod_fam AND products_per_puc.prod_fam <> ""\n        ',
                "cumulative_products_per_puc",
            ),
            reverse_code=django_db_views.migration_functions.BackwardViewMigration(
                "", "cumulative_products_per_puc"
            ),
            atomic=False,
        ),
        django_db_views.operations.ViewRunPython(
            code=django_db_views.migration_functions.ForwardViewMigration(
                "SELECT \n            1 as id,\n            product_uber_puc.puc_id AS puc_id,\n            dashboard_dsstoxlookup.id as dsstoxlookup_id ,\n            count(product_uber_puc.product_id) AS product_count\n        FROM\n            product_uber_puc\n            INNER JOIN\n            dashboard_productdocument ON (product_uber_puc.product_id = dashboard_productdocument.product_id)\n                INNER JOIN\n            dashboard_datadocument ON (dashboard_productdocument.document_id = dashboard_datadocument.id)\n                INNER JOIN\n            dashboard_rawchem ON (dashboard_datadocument.id = dashboard_rawchem.extracted_text_id)\n                INNER JOIN\n            dashboard_dsstoxlookup ON (dashboard_rawchem.dsstox_id = dashboard_dsstoxlookup.id)\n            GROUP BY product_uber_puc.puc_id, dashboard_dsstoxlookup.id\n            ",
                "products_per_puc_and_sid",
            ),
            reverse_code=django_db_views.migration_functions.BackwardViewMigration(
                "", "products_per_puc_and_sid"
            ),
            atomic=False,
        ),
        django_db_views.operations.ViewRunPython(
            code=django_db_views.migration_functions.ForwardViewMigration(
                'SELECT cumulative_union .* ,\n        COALESCE(products_per_puc_and_sid.product_count,0) as product_count\n        FROM\n        (SELECT  \n        -- gen cat\n        1 as id,\n        gencat_id.puc_id,\n        dsstoxlookup_id, \n        gencat_id.kind_id, \n        sum(products_per_puc_and_sid.product_count) as cumulative_product_count,\n        1 as puc_level\n        FROM \n        dashboard_puc \n        LEFT JOIN\n        products_per_puc_and_sid\n        ON products_per_puc_and_sid.puc_id = dashboard_puc.id\n        LEFT JOIN (select kind_id, gen_cat, min(id) as puc_id from dashboard_puc where prod_fam = "" and prod_type = "" GROUP BY kind_id, gen_cat) gencat_id\n        ON gencat_id.gen_cat = dashboard_puc.gen_cat AND gencat_id.kind_id = dashboard_puc.kind_id\n        GROUP BY dsstoxlookup_id, gencat_id.kind_id, gencat_id.gen_cat, gencat_id.puc_id\n        HAVING dsstoxlookup_id is not null\n        UNION \n        SELECT \n        -- prod fam\n        1 as id,\n        prodfam_id.puc_id,\n        dsstoxlookup_id, \n        prodfam_id.kind_id, \n        sum(products_per_puc_and_sid.product_count) as cumulative_product_count,\n        2 as puc_level\n        FROM \n        dashboard_puc \n        LEFT JOIN\n        products_per_puc_and_sid\n        ON products_per_puc_and_sid.puc_id = dashboard_puc.id\n        LEFT JOIN (select kind_id, gen_cat, prod_fam, min(id) as puc_id from dashboard_puc where prod_fam <> "" and prod_type = "" GROUP BY kind_id, gen_cat, prod_fam) prodfam_id\n        ON prodfam_id.gen_cat = dashboard_puc.gen_cat AND prodfam_id.kind_id = dashboard_puc.kind_id AND prodfam_id.prod_fam = dashboard_puc.prod_fam\n        WHERE dashboard_puc.prod_fam <> "" \n        GROUP BY  dsstoxlookup_id, prodfam_id.kind_id, prodfam_id.gen_cat, prodfam_id.puc_id, prodfam_id.prod_fam\n        -- exclude gen_cat\n        HAVING dsstoxlookup_id is not null\n        UNION \n        SELECT \n        -- prod_type\n        1 as id,\n        puc_id,\n        dsstoxlookup_id, \n        kind_id, \n        products_per_puc_and_sid.product_count as cumulative_product_count,\n        3 as puc_level\n        FROM \n        dashboard_puc \n        LEFT JOIN\n        products_per_puc_and_sid\n        ON products_per_puc_and_sid.puc_id = dashboard_puc.id\n        WHERE dashboard_puc.prod_type <> "" \n        AND dsstoxlookup_id is not null) cumulative_union\n        LEFT JOIN\n        products_per_puc_and_sid ON\n        products_per_puc_and_sid.puc_id = cumulative_union.puc_id\n        and products_per_puc_and_sid.dsstoxlookup_id = cumulative_union.dsstoxlookup_id',
                "cumulative_products_per_puc_and_sid",
            ),
            reverse_code=django_db_views.migration_functions.BackwardViewMigration(
                "", "cumulative_products_per_puc_and_sid"
            ),
            atomic=False,
        ),
    ]