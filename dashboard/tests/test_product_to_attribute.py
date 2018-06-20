from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User
# from django.core.exceptions import ValidationError

from dashboard.models import (DataSource, GroupType, DataGroup, DocumentType, DataDocument,
                              Script, ExtractedText, ExtractedChemical,
                              Product, ProductAttribute, ProductToAttribute)

class SimpleSetup(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Set up data for the whole TestCase
        print(('...setting up simple instances...\n'
              'self.user = User \n'
              'self.ds = DataSource \n'
              'self.script = Script \n'
              'self.gt = GroupType \n'
              'self.dg = DataGroup \n'
              'self.dt = DocumentType \n'
              'self.doc = DataDocument \n'))
        cls.user = User.objects.create_user(username='Karyn',
                                            password='specialP@55word')
        cls.ds = DataSource.objects.create(title='Data Source for Test',
                                            estimated_records=2, state='AT',
                                            priority='HI')
        cls.script = Script.objects.create(title='Test Title',
                                            url='http://www.epa.gov/',
                                            qa_begun=False, script_type='DL')
        cls.gt = GroupType.objects.create(title='Composition')
        cls.dg = DataGroup.objects.create(name='Data Group for Test',
                                            description='Testing...',
                                            data_source = cls.ds,
                                            download_script=cls.script,
                                            group_type = cls.gt,
                                            downloaded_by=cls.user,
                                            downloaded_at=timezone.now(),
                                            csv='register_records_matching.csv')
        cls.dt = DocumentType.objects.create(title='msds/sds', group_type=cls.gt)
        cls.doc = DataDocument.objects.create(title='test document',
                                                data_group=cls.dg,
                                                document_type=cls.dt)

        cls.p = Product.objects.create(data_source=cls.ds, title="Test Product", upc='stub_test')

##############################################################################

class ProductAttributeTest(SimpleSetup):

    def test_product_attribute_exists(self):
        '''@zach, the SimpleSetup is a class setup that I had simplified
        to try to use to inherit into all other classes thinking that we could setup a simple DB just once. It won't work this way unless we make tests
        like below all into one class, which I don't think is going to be our
        method for test creation, so the same functionality that is above could
        just be put into the "setUp" method, but this illustrates a tests that the many-to-many join is created through the "ProductToAttribute" model.
        '''

        a = ProductAttribute.objects.create(title='tang', type='ms')
        self.assertFalse(self.p.productattribute_set.exists())
        self.assertEqual(len(ProductToAttribute.objects.all()), 0, "There should be no Product linked to ProductAttribute")
        c = ProductToAttribute.objects.create(product=self.p,
                                              product_attribute=a)
        self.assertTrue(self.p.productattribute_set.exists())
        self.assertEqual(len(ProductToAttribute.objects.all()), 1, "There should be Product linked to ProductAttribute")
