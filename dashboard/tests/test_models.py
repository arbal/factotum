from django.contrib.auth.models import User
from dashboard.models import DataSource, GroupType, DataGroup, DocumentType, DataDocument, ExtractedText,\
    ExtractedChemical, UnitType, WeightFractionType, DSSToxSubstance, Script, Product, ProductDocument,\
    Ingredient, ProductToIngredient, DSSToxSubstanceToIngredient, ProductAttribute, ProductToAttribute
from django.test import TestCase, RequestFactory
from django.utils import timezone
import csv
import collections
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import FileSystemStorage


def file_len(fname):
    with open(fname) as f:
        for i, l in enumerate(f):
            pass
    f.closed
    return i + 1


class ModelsTest(TestCase):

    def setUp(self):
        # Every test needs access to the request factory.
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='jdoe', email='jon.doe@epa.gov', password='Sup3r_secret')
        self.client.login(username='jdoe', password='Sup3r_secret')

        # DataSource
        self.ds = self.create_data_source()

        # Script, type DL
        self.dl = self.create_download_script(script_type='DL')

        # GroupType
        self.gt = self.create_group_type()

        # DataGroup
        self.dg = self.create_data_group(data_source=self.ds, download_script=self.dl, group_type=self.gt)
        self.pdfs = self.upload_pdfs()

        # DocumentType
        self.dt = self.create_document_type(group_type=self.gt)

        # DataDocuments
        self.dds = self.create_data_documents(data_group = self.dg, document_type = self.dt)

        # Script, type EX
        self.ex = self.create_extraction_script(script_type='EX')

        # ExtractedText
        self.et = self.create_extracted_text(data_documents=self.dds, extraction_script=self.ex)

        # UnitType
        self.ut = self.create_unit_type(title='percent composition')

        # WeightFractionType
        self.wft = self.create_weight_fraction_type(title= 'reported', description= 'reported')

        # ExtractedChemical
        self.ec = self.create_extracted_chemical(extracted_text=self.et,
                                                 unit_type=UnitType.objects.all()[0],
                                                 weight_fraction_type = WeightFractionType.objects.all()[0]
                                                )

        # DSSToxSubstance
        self.dsstox = self.create_dsstox_substance(extracted_chemical=self.ec)

        # Product
        self.p = Product.objects.create(data_source=self.ds, title="Test Product")
        self.p.save()

        # ProductDocument
        self.pd = ProductDocument.objects.create(product=self.p, document=self.dds[0])

        # Ingredient
        self.i = self.create_ingredient(self.wft)
        self.i.save()

        # ProductToIngredient
        self.pi = ProductToIngredient.objects.create(product=self.p, ingredient=self.i)

        # DSSToxSubstanceToIngredient
        self.dsi = DSSToxSubstanceToIngredient.objects.create(dsstox_substance=self.dsstox, ingredient=self.i)

        # ProductAttribute
        self.pa = ProductAttribute.objects.create(title="Test Product Attribute")
        self.pa.save()

    def tearDown(self):
        del self.dg

    def create_data_source(self, title='Data Source for Test', estimated_records=2, state='AT', priority='HI'):
        return DataSource.objects.create(title=title, estimated_records=estimated_records, state=state,
                                         priority=priority)

    def create_download_script(self, script_type, title='Test Title', url='http://www.epa.gov/', qa_begun=False):
        return Script.objects.create(title=title, url=url, qa_begun=qa_begun, script_type=script_type)

    def create_group_type(self):
        return GroupType.objects.create(title='Composition')

    def create_data_group(self, data_source, download_script, group_type, testusername = 'jdoe', name='Data Group for Test',
                          description='Testing the DataGroup model'):
            source_csv = open('./sample_files/register_records_matching.csv', 'rb')
            return DataGroup.objects.create(name=name,
                                            description=description, data_source = data_source,
                                            group_type=group_type,
                                            download_script=download_script,
                                            downloaded_by=User.objects.get(username=testusername),
                                            downloaded_at=timezone.now(),
                                            csv=SimpleUploadedFile('register_records_matching.csv', source_csv.read() )
                                            )

    def upload_pdfs(self):
        store = settings.MEDIA_URL + self.dg.dgurl()
        pdf1_name = '0bf5755e-3a08-4024-9d2f-0ea155a9bd17.pdf'
        pdf2_name = '0c68ab16-2065-4d9b-a8f2-e428eb192465.pdf'
        local_pdf = open('./sample_files/' + pdf1_name, 'rb')
        fs = FileSystemStorage(store + '/pdf')
        fs.save(pdf1_name, local_pdf)
        local_pdf = open('./sample_files/' + pdf2_name, 'rb')
        fs = FileSystemStorage(store + '/pdf')
        fs.save(pdf2_name, local_pdf)
        return [pdf1_name, pdf2_name]

    def create_document_type(self, group_type):
        return DocumentType.objects.create(title='msds/sds', group_type=group_type)

    def create_data_documents(self, data_group, document_type):
        dds = []
        gt = self.create_group_type()
        dt = self.create_document_type(group_type=gt)
        with open(data_group.csv.path) as dg_csv:
            table = csv.DictReader(dg_csv)
            text = ['DataDocument_id,' + ','.join(table.fieldnames)+'\n']
            errors = []
            count = 0
            for line in table: # read every csv line, create docs for each
                count+=1
                if line['filename'] == '':
                    errors.append(count)
                if line['title'] == '': # updates title in line object
                    line['title'] = line['filename'].split('.')[0]
                dd = DataDocument.objects.create(filename=line['filename'],
                    title=line['title'],
                    document_type=DocumentType.objects.get(pk=line['document_type']),
                    product_category=line['product'],
                    url=line['url'],
                    matched = line['filename'] in self.pdfs,
                    data_group=data_group,
                    )
                dd.save()
                dds.append(dd)
            return dds

    def create_extraction_script(self, script_type, title='Test Title', url='http://www.epa.gov/', qa_begun=False):
        return Script.objects.create(title=title, url=url, qa_begun=qa_begun, script_type=script_type)

    def create_extracted_text(self, data_documents, extraction_script):
        return ExtractedText.objects.create(data_document=data_documents[0], record_type='Test Record Type',
                                            prod_name='Test Prod Name', doc_date='TstDocDate', rev_num='Test Rev Num',
                                            extraction_script=extraction_script, qa_checked=False)

    def create_unit_type(self, title='percent composition'):
        return UnitType.objects.create(title=title)
    
    def create_weight_fraction_type(self, title= 'reported', description= 'reported'):
        return WeightFractionType.objects.create(title=title, description=description)

    def create_extracted_chemical(self, extracted_text, raw_cas='Test CAS', raw_chem_name='Test Chem Name',
                                  raw_min_comp='Test Raw Min Comp', raw_max_comp='Test Raw Max Comp',
                                  unit_type=UnitType.objects.first(), 
                                  weight_fraction_type=WeightFractionType.objects.first(), 
                                  report_funcuse='Test Report Funcuse'):
        return ExtractedChemical.objects.create(extracted_text=extracted_text, raw_cas=raw_cas,
                                                raw_chem_name=raw_chem_name, raw_min_comp=raw_min_comp,
                                                raw_max_comp=raw_max_comp, unit_type=unit_type, 
                                                weight_fraction_type=weight_fraction_type,
                                                report_funcuse=report_funcuse)

    def create_dsstox_substance(self, extracted_chemical, true_cas='Test True CAS',
                                true_chemname='Test Chem Name', rid='Test RID', sid='Test SID'):
        return DSSToxSubstance.objects.create(extracted_chemical=extracted_chemical, true_cas=true_cas,
                                              true_chemname=true_chemname, rid=rid, sid=sid)


    def create_ingredient(self, weight_fraction_type, lower_wf_analysis=0.123456789012345,
                          central_wf_analysis=0.2, upper_wf_analysis = 1):
        return Ingredient.objects.create(weight_fraction_type = weight_fraction_type,
                                         lower_wf_analysis = lower_wf_analysis,
                                         central_wf_analysis = central_wf_analysis,
                                         upper_wf_analysis = upper_wf_analysis)

    def test_object_creation(self):
        self.assertTrue(isinstance(self.ds, DataSource))
        self.assertTrue(isinstance(self.dg, DataGroup))
        self.assertTrue(isinstance(self.dds, collections.Iterable))
        self.assertTrue(isinstance(self.ex, Script))
        self.assertTrue(isinstance(self.et, ExtractedText))
        self.assertTrue(isinstance(self.ec, ExtractedChemical))
        self.assertTrue(isinstance(self.dsstox, DSSToxSubstance))
        self.assertTrue(isinstance(self.i, Ingredient))
        self.assertTrue(isinstance(self.p, Product))
        self.assertTrue(isinstance(self.pi, ProductToIngredient))
        self.assertTrue(isinstance(self.pd, ProductDocument))
        self.assertTrue(isinstance(self.dsi, DSSToxSubstanceToIngredient))
        self.assertTrue(isinstance(self.pa, ProductAttribute))

    def test_object_properties(self):
        # Test properties of objects
        # DataSource
        self.assertEqual(self.ds.__str__(), self.ds.title)

        # DataGroup
        self.assertEqual(self.dg.__str__(), self.dg.name)
        self.assertEqual(self.dg.dgurl(), self.dg.name.replace(' ', '_'))
        # The number of rows in the DataGroup's uploaded csv should match the rows in the local copy
        csv_there = file_len(self.dg.csv.path)
        csv_here  = file_len('./sample_files/register_records_matching.csv')
        self.assertEqual(csv_there, csv_here)

        # DataDocuments
        # The number of data documents created should match the number of rows in the csv file minus the header
        self.assertEqual(len(self.dds) , csv_there - 1)
        # Confirm that one of the data documents appears in the data group show page
        dg_response = self.client.get('/datagroup/' + str(self.dg.pk), follow=True)
        self.assertIn(b'NUTRA', dg_response.content)
        self.assertEqual(len(self.pdfs), 2)
        # Confirm that the two data documents in the csv file are matches to the pdfs via their file names
        self.assertEqual(self.dg.matched_docs(), 2)
        # Test a link to an uploaded pdf
        good_url = b'Data_Group_for_Test/pdf/0bf5755e-3a08-4024-9d2f-0ea155a9bd17.pdf'
        self.assertIn(good_url, dg_response.content)

        # ExtractionScript
        self.assertEqual(self.ex.__str__(), 'Test Title')

        # ExtractedText
        self.assertEqual(self.et.__str__(), 'Test Prod Name')

        # ExtractedChemical
        self.assertEqual(self.ec.__str__(), 'Test Chem Name')

        # DSSToxSubstance
        self.assertEqual(self.dsstox.__str__(), self.ec.__str__())

    def test_product_attribute(self):
        p2a = ProductToAttribute.objects.create(product=self.p, product_attribute=self.pa)
        p2a.save()
        self.assertEqual(ProductToAttribute.objects.count(), 1)
