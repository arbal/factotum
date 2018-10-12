from django.utils import timezone
from django.contrib.auth.models import User

from dashboard.models import *

fixtures_standard = ['00_superuser.yaml','01_lookups.yaml','02_datasource.yaml','03_datagroup.yaml',
                    '04_PUC.yaml','05_product.yaml','06_datadocument.yaml','07_script.yaml',
                    '08_extractedtext.yaml','09_productdocument.yaml','10_extractedchemical.yaml',
                     '11_dsstoxsubstance.yaml']

class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

def load_model_objects():
    user = User.objects.create_user(username='Karyn',
                                        password='specialP@55word')
    ds = DataSource.objects.create(title='Data Source for Test',
                                        estimated_records=2, state='AT',
                                        priority='HI')
    script = Script.objects.create(title='Test Download Script',
                                        url='http://www.epa.gov/',
                                        qa_begun=False, script_type='DL')
    exscript = Script.objects.create(title='Test Extraction Script',
                                   url='http://www.epa.gov/',
                                   qa_begun=False, script_type='EX')
    gt = GroupType.objects.create(title='Composition')
    dg = DataGroup.objects.create(name='Data Group for Test',
                                        description='Testing...',
                                        data_source = ds,
                                        download_script=script,
                                        downloaded_by=user,
                                        downloaded_at=timezone.now(),
                                        group_type=gt,
                                        csv='register_records_matching.csv',
                                        url='https://www.epa.gov')
    dt = DocumentType.objects.create(title='msds/sds', group_type=gt)
    doc = DataDocument.objects.create(title='test document',
                                            data_group=dg,
                                            document_type=dt,
                                            filename='example.pdf')
    p = Product.objects.create(data_source=ds,
                                upc='Test UPC for ProductToPUC')

    puc = PUC.objects.create(gen_cat='Test General Category',
                              prod_fam='Test Product Family',
                              prod_type='Test Product Type',
                             description='Test Product Description',
                             last_edited_by = user)

    extext = ExtractedText.objects.create(
                                    prod_name='Test Extracted Text Record',
                                    data_document=doc,
                                    extraction_script=exscript
                                    )
    ut = UnitType.objects.create(title='percent composition')
    wft = WeightFractionType.objects.create(title= 'reported', description= 'reported')
    ing = Ingredient.objects.create(lower_wf_analysis = 0.123456789012345,
                                     central_wf_analysis = 0.2,
                                     upper_wf_analysis = 1,
                                     script = script)
    ec = ExtractedChemical.objects.create(raw_chem_name= 'Test Chem Name',
                                            extracted_text=extext,
                                            unit_type=ut,
                                            weight_fraction_type = wft,
                                            ingredient = ing)
    dsstox = DSSToxSubstance.objects.create(extracted_chemical=ec,
                                            true_chemname='Test Chem Name')
    pa = ProductAttribute.objects.create(title="Test Product Attribute")
    pd = ProductDocument.objects.create(product=p, document=doc)
    ehp = ExtractedHabitsAndPractices.objects.create(extracted_text=extext,
                                                     product_surveyed='Test Product Surveyed',
                                                     prevalence='Continuous')


    return dotdict({'user':user,
                    'ds':ds,
                    'script':script,
                    'exscript':exscript,
                    'dg':dg,
                    'doc':doc,
                    'p':p,
                    'puc':puc,
                    'extext':extext,
                    'ut':ut,
                    'wft':wft,
                    'ec':ec,
                    'dsstox':dsstox,
                    'pa':pa,
                    'pd':pd,
                    'ing':ing,
                    'dt':dt,
                    'gt':gt,
                    'ehp':ehp
                    })
