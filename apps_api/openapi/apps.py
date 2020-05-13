import os

from django.apps import AppConfig
from django.utils.autoreload import autoreload_started
from django.utils.translation import gettext_lazy as _


def jsonnet_watchdog(sender, **kwargs):
    """Restart runserver on jsonnet file changes."""
    schema_dir = os.path.join(os.path.dirname(__file__), "schemas")
    sender.watch_dir(schema_dir, "**/*.libsonnet")
    sender.watch_dir(schema_dir, "**/*.jsonnet")


class OpenAPIConfig(AppConfig):
    name = "apps_api.openapi"
    verbose_name = _("OpenAPI")

    def ready(self):
        autoreload_started.connect(jsonnet_watchdog)
