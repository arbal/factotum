from django.db import connection
from pathlib import Path


def fetch_dashboard_logstash(**kwargs):
    "Return all rows from the logstash query as a dict"
    querysql = Path("../factotum_elastic/logstash/query.sql").read_text()
    where_sql = kwargs.get("where", None)
    if where_sql:
        querysql = querysql + " " + where_sql
    # querysql = querysql.replace('\n', '')
    with connection.cursor() as cursor:
        cursor.execute(querysql)
        columns = [col[0] for col in cursor.description]
        indexed = [dict(zip(columns, row)) for row in cursor.fetchall()]

    return indexed

def shell_logstash_populate():
    """
    Utility method to pull selected records from prod data into the index
    """
    from django.conf import settings
    import base64
    import requests
    esurl = settings.ELASTICSEARCH["default"]["HOSTS"][0]
    index = settings.ELASTICSEARCH["default"]["INDEX"]
    (es_username, es_password) = settings.ELASTICSEARCH["default"][
        "HTTP_AUTH"
    ]
    auth_header = {
        "Authorization": "Basic "
        + base64.b64encode(
            f"{es_username}:{es_password}".encode("utf-8")
        ).decode("utf-8")
    }

    # PUC = 259 (Pet shampoo) or PUC = 210 (shampoo)
    docs_json = fetch_dashboard_logstash(where="WHERE puc_id IN (259, 210)")
    for doc_dict in docs_json:
        # add the JSON to the index
        response = requests.post(
            f"http://{esurl}/dashboard/_doc/",
            json=doc_dict,
            headers=auth_header,
        )

