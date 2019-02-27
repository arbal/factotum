import io
from lxml import html

from django.utils import timezone
from django.test import RequestFactory, TestCase, override_settings
from django.core.files.uploadedfile import InMemoryUploadedFile

from dashboard.models import *
from dashboard.tests.loader import *
from dashboard.views.data_group import DataGroupForm, data_group_create


@override_settings(ALLOWED_HOSTS=['testserver'])
class DataGroupFormTest(TestCase):
    fixtures = fixtures_standard

    def setUp(self):
        self.factory = RequestFactory()
        self.client.login(username='Karyn', password='specialP@55word')

    def test_detail_form_url(self):
        self.assertTrue(DataGroupForm().fields['url'],
                        'DataGroupForm should include the url')

        dg = DataGroup.objects.get(pk=6)
        response = self.client.post(f'/datagroup/edit/{dg.pk}/',
                                    {'name': dg.name,
                                    'url': 'http://www.epa.gov',
                                    'group_type': dg.group_type_id,
                                    'downloaded_by': dg.downloaded_by_id,
                                    'downloaded_at': dg.downloaded_at,
                                    'data_source': dg.data_source_id})
        dg.refresh_from_db()
        dg = DataGroup.objects.get(pk=dg.pk)
        self.assertEqual(dg.url, 'http://www.epa.gov',
                     f'DataDocument {dg.pk} should have the url "http://www.epa.gov"')

    def test_detail_form_group_type(self):
        # DG 6 has extracted docs, so group_type should be disabled, and a forced update should fail
        dg = DataGroup.objects.get(pk=6)
        response = self.client.get(f'/datagroup/edit/{str(dg.pk)}/').content.decode('utf8')
        response_html = html.fromstring(response)
        self.assertTrue(response_html.xpath('//*[@id="id_group_type"][@disabled]'),
                      'The group_type select box should be disabled')
        response = self.client.post(f'/datagroup/edit/{dg.pk}/',
                                    {'name': dg.name,
                                    'url': 'http://www.epa.gov',
                                    'group_type': dg.group_type_id + 1,
                                    'downloaded_by': dg.downloaded_by_id,
                                    'downloaded_at': dg.downloaded_at,
                                    'data_source': dg.data_source_id})

        response_html = html.fromstring(response.content.decode('utf8'))
        self.assertTrue(response_html.xpath('//*[@id="id_group_type"]/following::div[@class="invalid-feedback"]'),
                      'Changing the group_type when extracted_docs exists should raise a ValidationError')

    def test_register_records_header(self):
        ds_pk = DataSource.objects.first().pk
        csv_string = (
                    "filename,title,document_type,product,url,organization"
                    "1.pdf,Home Depot,2,,www.homedepot.com/594.pdf,"
                    "2.pdf,Home Depot,2,,www.homedepot.com/fb5.pdf,"
                    )
        csv_string_bytes = csv_string.encode(encoding='UTF-8',errors='strict' )
        in_mem_sample_csv = InMemoryUploadedFile(
                io.BytesIO(csv_string_bytes),
                field_name='register_records',
                name='register_records.csv',
                content_type='text/csv',
                size=len(csv_string),
                charset='utf-8',
        )
        data={'name':'Slinky','group_type':1,'downloaded_by':1,
                'downloaded_at':timezone.now(),'download_script':1,
                'data_source':ds_pk,'csv':in_mem_sample_csv
        }
        req = self.factory.post(path=f'/datasource/{ds_pk}/datagroup_new/',
                                data=data)
        req.user = User.objects.get(username='Karyn')
        resp = data_group_create(request=req, pk=6)
        self.assertContains(resp,'CSV column headers are incorrect for upload')


