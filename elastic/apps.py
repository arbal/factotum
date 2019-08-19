from elasticsearch_dsl import connections

from django.apps import AppConfig
from django.conf import settings


class ElasticConfig(AppConfig):
    name = "elastic"

    def _lower_dict(self, d):
        out = {}
        for k, v in d.items():
            if type(v) == dict:
                v = self._lower_dict(v)
            out[k.lower()] = v
        return out

    def ready(self):
        connections.configure(**self._lower_dict(settings.ELASTICSEARCH))
