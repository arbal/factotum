from django.db import migrations, connection


def create_views(apps, schema_editor):
    sql_cmd = ""
    # create the rawchem to datadocument relationships
    sql_cmd += """
        CREATE VIEW `logstash.rawchem==datadocument` AS
            SELECT
                rc.id AS rawchem_id,
                dd.id AS datadocument_id
            FROM
                dashboard_rawchem rc
                LEFT JOIN dashboard_extractedtext et ON rc.extracted_text_id = et.data_document_id
                LEFT JOIN dashboard_datadocument dd ON et.data_document_id = dd.id;
        CREATE VIEW `logstash.rawchem!=datadocument` AS
            SELECT
                NULL AS rawchem_id,
                dd.id AS datadocument_id
            FROM
                dashboard_datadocument dd
            WHERE
                dd.id NOT IN (SELECT data_document_id FROM dashboard_extractedtext WHERE data_document_id IS NOT NULL);
        CREATE VIEW `logstash.rawchem|datadocument` AS
            SELECT * FROM `logstash.rawchem==datadocument`
            UNION ALL
            SELECT * FROM `logstash.rawchem!=datadocument`;
    """
    # create the datadocument to product relationships
    sql_cmd += """
        CREATE VIEW `logstash.datadocument==product` AS
            SELECT
                rc_dd.datadocument_id AS datadocument_id,
                p.id AS product_id
            FROM
                (SELECT datadocument_id FROM `logstash.rawchem==datadocument` WHERE datadocument_id IS NOT NULL GROUP BY datadocument_id) rc_dd
                LEFT JOIN dashboard_productdocument pd ON rc_dd.datadocument_id = pd.document_id
                LEFT JOIN dashboard_product p ON pd.product_id = p.id;
        CREATE VIEW `logstash.datadocument!=product` AS
            SELECT
                NULL AS datadocument_id,
                p.id AS product_id
            FROM
                dashboard_product p
            WHERE
                p.id NOT IN (SELECT product_id FROM dashboard_productdocument WHERE product_id IS NOT NULL);
        CREATE VIEW `logstash.datadocument|product` AS
            SELECT * FROM `logstash.datadocument==product`
            UNION ALL
            SELECT * FROM `logstash.datadocument!=product`;
    """
    # create the product to puc relationships
    sql_cmd += """
        CREATE VIEW `logstash.product==puc` AS
            SELECT
                dd_p.product_id AS product_id,
                puc.id AS puc_id
            FROM
                (SELECT product_id FROM `logstash.datadocument==product` WHERE product_id IS NOT NULL GROUP BY product_id) dd_p
                LEFT JOIN dashboard_producttopuc pp ON dd_p.product_id = pp.product_id
                LEFT JOIN dashboard_puc puc ON pp.product_id = puc.id;
        CREATE VIEW `logstash.product!=puc` AS
            SELECT
                NULL AS product_id,
                puc.id AS puc_id
            FROM
                dashboard_puc puc
            WHERE
                puc.id NOT IN (SELECT puc_id FROM `logstash.product==puc` WHERE puc_id IS NOT NULL);
        CREATE OR REPLACE VIEW `logstash.product|puc` AS
            SELECT * FROM `logstash.product==puc`
            UNION ALL
            SELECT * FROM `logstash.product!=puc`;
    """
    # "full outer join" all id's
    sql_cmd += """
        CREATE VIEW `logstash.id|id` AS
            SELECT
                rawchem_id,
                datadocument_id,
                product_id,
                puc_id 
            FROM
                `logstash.rawchem|datadocument`
                NATURAL LEFT JOIN `logstash.datadocument|product`
                NATURAL LEFT JOIN `logstash.product|puc`
            UNION
            SELECT
                rawchem_id,
                datadocument_id,
                product_id,
                puc_id 
            FROM
                `logstash.rawchem|datadocument`
                NATURAL RIGHT JOIN `logstash.datadocument|product`
                NATURAL LEFT JOIN `logstash.product|puc`
            UNION
            SELECT
                rawchem_id,
                datadocument_id,
                product_id,
                puc_id
            FROM
                `logstash.rawchem|datadocument`
                NATURAL RIGHT JOIN `logstash.datadocument|product`
                NATURAL RIGHT JOIN `logstash.product|puc`;
    """
    with connection.cursor() as c:
        c.execute(sql_cmd)


def drop_views(apps, schema_editor):
    sql_cmd = ""
    # drop the rawchem to datadocument relationships
    sql_cmd += "DROP VIEW `logstash.rawchem==datadocument`;"
    sql_cmd += "DROP VIEW `logstash.rawchem!=datadocument`;"
    sql_cmd += "DROP VIEW `logstash.rawchem|datadocument`;"
    sql_cmd += "DROP VIEW `logstash.datadocument==product`;"
    sql_cmd += "DROP VIEW `logstash.datadocument!=product`;"
    sql_cmd += "DROP VIEW `logstash.datadocument|product`;"
    sql_cmd += "DROP VIEW `logstash.product==puc`;"
    sql_cmd += "DROP VIEW `logstash.product!=puc`;"
    sql_cmd += "DROP VIEW `logstash.product|puc`;"
    sql_cmd += "DROP VIEW `logstash.id|id`;"
    with connection.cursor() as c:
        c.execute(sql_cmd)


class Migration(migrations.Migration):

    dependencies = [("dashboard", "0120_auto_20190712_1054")]

    operations = [migrations.RunPython(create_views, drop_views)]
