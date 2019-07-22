from django.core import management
from django.core.management import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):

        print("dropping and re-creating schema...")
        management.call_command("reset_db", "--noinput")

        print("making migrations if necessary...")
        management.call_command("makemigrations")

        print("applying migrations...")
        management.call_command("migrate")

        print("loading fixtures...")
        management.call_command("loadalldata")

        self.stdout.write(
            self.style.SUCCESS("Successfully rebuilt db and started server")
        )
