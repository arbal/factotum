from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

import black
import git
import pathlib
from pyflakes import api as pyflakes


class Command(BaseCommand):
    help = "Lints and fixes code"

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-fix", action="store_true", help="Just lint, don't fix files"
        )
        parser.add_argument(
            "--no-lint", action="store_true", help="Just fix, don't lint files"
        )
        parser.add_argument(
            "--all", action="store_true", help="Lint all files, not just changed files"
        )

    def handle(self, *args, **options):
        root = pathlib.Path(settings.BASE_DIR)
        g_args = ["--exclude-standard", "-X", root.joinpath(".lintignore")]
        if not options["all"]:
            g_args.append("-m")
        files_str = git.Git(settings.BASE_DIR).ls_files(g_args)
        del_files_str = git.Git(settings.BASE_DIR).ls_files("-d", "-k")
        files = set(
            pathlib.Path(p) for p in files_str.splitlines() if p[-3:] == ".py"
        ) - set(pathlib.Path(p) for p in del_files_str.splitlines())
        num_lint_errors = 0
        num_black_formats = 0
        for p in files:
            if not options["no_fix"]:
                changed = black.format_file_in_place(
                    p, False, black.FileMode(), black.WriteBack.YES
                )
                if changed:
                    num_black_formats += 1
                    self.stdout.write("%s: Black formatted file" % str(p))
            if not options["no_lint"]:
                num_lint_errors += pyflakes.checkPath(str(p))
        if num_black_formats:
            raise CommandError("%i file(s) formatted by Black" % num_black_formats)
        if num_lint_errors:
            raise CommandError("%i liniting error(s) found" % num_lint_errors)
