from django.contrib.auth.models import User
from django.test import TestCase
from django.utils.timezone import now

from dashboard.forms import create_detail_formset
from dashboard.forms.forms import ExtractedTextFUForm, ExtractedTextHPForm
from dashboard.models import DataDocument, GroupType, DataGroup, DataSource
from dashboard.tests.loader import load_model_objects


class ExtractedTextFormsTest(TestCase):
    def setUp(self):
        self.client.login(username="Karyn", password="specialP@55word")

    @classmethod
    def setUpTestData(cls):
        cls.objects = load_model_objects()
        # Add functional use Grouptype, DataGroup and DataDoc for test_functional_use_forms (could be a test case)
        cls.group_type = GroupType.objects.create(code="FU", title="Functional Use")
        cls.data_group = DataGroup.objects.create(
            group_type=cls.group_type,
            downloaded_at=now(),
            downloaded_by=User.objects.first(),
            data_source=DataSource.objects.first(),
        )
        cls.data_doc = DataDocument.objects.create(data_group=cls.data_group)

        # Add HP grouptype
        cls.hp_group_type = GroupType.objects.create(
            code="HP", title="Habits and Practices"
        )
        cls.hp_data_group = DataGroup.objects.create(
            group_type=cls.hp_group_type,
            downloaded_at=now(),
            downloaded_by=User.objects.first(),
            data_source=DataSource.objects.first(),
        )
        cls.hp_doc = DataDocument.objects.create(data_group=cls.hp_data_group)

    def test_functional_use_forms(self):
        functional_document = DataDocument.objects.filter(
            data_group__group_type__code="FU"
        ).first()
        form, _ = create_detail_formset(functional_document)
        self.assertEqual(form, ExtractedTextFUForm)
        fields = form.base_fields.keys()
        self.assertEquals(set(fields), {"doc_date", "rev_num"})

    def test_hp_forms(self):
        form, _ = create_detail_formset(self.hp_doc)
        self.assertEqual(form, ExtractedTextHPForm)
        fields = form.base_fields.keys()
        self.assertEquals(set(fields), {"doc_date", "rev_num", "extraction_completed"})
