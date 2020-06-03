from django.test import TestCase
from dashboard.tests.loader import *
from dashboard.models import GroupType
from django.db.utils import IntegrityError


class DataGroupTest(TestCase):
    fixtures = fixtures_standard

    def test_group_type_code_unique(self):
        group_type = GroupType.objects.get(pk=1)
        with self.assertRaises(IntegrityError):
            new_group_type = GroupType.objects.create(
                title="Test", code=group_type.code
            )

    def test_hh_group_no_bulk_assign_form(self):
        group_type = GroupType.objects.get(code="HH")
        datagroup = DataGroup.objects.get(group_type=group_type)
        self.assertFalse(datagroup.include_bulk_assign_form())
