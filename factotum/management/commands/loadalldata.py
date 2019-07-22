from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.core import management
from django.conf import settings
import os


class Command(BaseCommand):
    help = "Loads all the YAML fixtures included in this app"

    def fixture_dirs(self):
        dirs = []
        fixture_dirs = settings.FIXTURE_DIRS
        if len(fixture_dirs) != len(set(fixture_dirs)):
            raise ImproperlyConfigured("settings.FIXTURE_DIRS contains duplicates.")
        for app_config in apps.get_app_configs():
            app_label = app_config.label
            app_dir = os.path.join(app_config.path, "fixtures")
            if app_dir in fixture_dirs:
                raise ImproperlyConfigured(
                    "'%s' is a default fixture directory for the '%s' app "
                    "and cannot be listed in settings.FIXTURE_DIRS."
                    % (app_dir, app_label)
                )
            if os.path.isdir(app_dir):
                dirs.append(app_dir)
        dirs.extend(fixture_dirs)
        dirs.append("")
        return [os.path.realpath(d) for d in dirs]

    def handle(self, *args, **options):
        fix_dirs = self.fixture_dirs()
        fx_list = []
        for p in fix_dirs:
            d = os.listdir(path=p)
            d.sort()
            for fn in d:
                if fn[-4:] == "yaml":
                    fx_list.append(fn[:-5])
        management.call_command("loaddata", *fx_list, **options)
