from django.db import migrations, connection


def update_id_view(apps, schema_editor):
    sql_cmd = """
        CREATE OR REPLACE VIEW `logstash.id|id` AS
                SELECT
                    dd.id AS datadocument_id,
                    rc.id AS rawchem_id,
                    p.id AS product_id,
                    puc.id AS puc_id
                FROM
                    dashboard_datadocument dd
                    LEFT JOIN dashboard_rawchem rc ON dd.id = rc.extracted_text_id
                    LEFT JOIN dashboard_productdocument pd ON dd.id = pd.document_id
                    LEFT JOIN dashboard_product p ON pd.product_id = p.id
                    LEFT JOIN dashboard_producttopuc pp ON p.id = pp.product_id
                    LEFT JOIN dashboard_puc puc ON pp.puc_id = puc.id
            UNION ALL
                SELECT
                    NULL AS datadocument_id,
                    NULL AS rawchem_id,
                    NULL AS product_id,
                    puc.id AS puc_id
                FROM
                    dashboard_puc puc
                    LEFT JOIN dashboard_producttopuc pp ON puc.id = pp.id
                    WHERE pp.id IS NULL;
    """
    with connection.cursor() as c:
        c.execute(sql_cmd)


def drop_old_views(apps, schema_editor):
    sql_cmd = ""
    sql_cmd += "DROP VIEW `logstash.rawchem==datadocument`;"
    sql_cmd += "DROP VIEW `logstash.rawchem!=datadocument`;"
    sql_cmd += "DROP VIEW `logstash.rawchem|datadocument`;"
    sql_cmd += "DROP VIEW `logstash.datadocument==product`;"
    sql_cmd += "DROP VIEW `logstash.datadocument!=product`;"
    sql_cmd += "DROP VIEW `logstash.datadocument|product`;"
    sql_cmd += "DROP VIEW `logstash.product==puc`;"
    sql_cmd += "DROP VIEW `logstash.product!=puc`;"
    sql_cmd += "DROP VIEW `logstash.product|puc`;"
    with connection.cursor() as c:
        c.execute(sql_cmd)


class Migration(migrations.Migration):

    dependencies = [("elastic", "0001_logstash_views")]

    operations = [
        migrations.RunPython(update_id_view),
        migrations.RunPython(drop_old_views),
    ]
