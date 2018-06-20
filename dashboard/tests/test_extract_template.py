from django.utils import timezone
from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.test import TestCase, RequestFactory

from dashboard.models import (DataSource, GroupType, DataGroup, Script,
                              ExtractedText, ExtractedChemical)

class ModelsTest(TestCase):

    def setUp(self):

        self.user = User.objects.create_user(
            username='Karyn', email='jon.doe@epa.gov',
            password='specialP@55word')
        
        self.client.login(username='Karyn', password='specialP@55word')

        self.ds = DataSource.objects.create(title='Data Source for Test',
                                            estimated_records=2, state='AT',
                                            priority='HI')

        self.dl = Script.objects.create(title='Test Title',
                                        url='http://www.epa.gov/',
                                        qa_begun=False, script_type='DL')

        self.gt = GroupType.objects.create(title='Composition')

        self.dg = DataGroup.objects.create(name='Data Group for Test',
                                    description='Testing the DataGroup model',
                                    data_source = self.ds,
                                    download_script=self.dl,
                                    downloaded_by=self.user,
                                    downloaded_at=timezone.now(),
                                    group_type=self.gt,
                                    csv='register_records_matching.csv')

    def test_template_colnames(self):
        fields = (ExtractedText._meta.get_fields() +
                                        ExtractedChemical._meta.get_fields())
        # get valid names from the 2 models that will be populated from csv
        valid_names = [field.name for field in fields]
        response = self.client.get(f'/datagroup/{self.dg.pk}')
        # test that first 2 columns link to DataDocument (pk/filename)
        self.assertEqual(response.context['extract_fieldnames'][:2],
                        ['data_document_pk', 'data_document_filename'],
                        'First 2 column names should link to data document.')
        # test that each column is in model attributes
        for colname in response.context['extract_fieldnames'][2:]:
            self.assertIn(colname,valid_names, f'{colname} not in the models')
