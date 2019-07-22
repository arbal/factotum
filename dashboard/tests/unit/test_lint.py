from django.test import SimpleTestCase, tag
from django.conf import settings

import black
import git
import os
import pathlib
from pyflakes import api as pyflakes
from pyflakes.reporter import Reporter


@tag("lint")
class LintTest(SimpleTestCase):
    def setUp(self):
        root = pathlib.Path(settings.BASE_DIR)
        g_args = ("--exclude-standard", "-X", root.joinpath(".lintignore"))
        files_str = git.Git(settings.BASE_DIR).ls_files(g_args)
        del_files_str = git.Git(settings.BASE_DIR).ls_files("-d", "-k")
        self.files = set(
            pathlib.Path(p) for p in files_str.splitlines() if p[-3:] == ".py"
        ) - set(pathlib.Path(p) for p in del_files_str.splitlines())
        self.devnull = open(os.devnull, "w")

    def test_black(self):
        for p in self.files:
            not_changed = black.format_file_in_place(
                p, False, black.FileMode(), black.WriteBack.NO
            )
            self.assertFalse(not_changed, "Found files not formatted by Black.")

    # def test_pyflakes(self):
    #    for p in self.files:
    #        not_linted = bool(
    #            pyflakes.checkPath(
    #                str(p), reporter=Reporter(self.devnull, self.devnull)
    #            )
    #        )
    #        self.assertFalse(not_linted, "Found files with linting errors.")
