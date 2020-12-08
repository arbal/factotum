from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from dashboard.tests.factories import *

from dashboard.models import (
    ExtractedText,
    ExtractedComposition,
    ExtractedHabitsAndPractices,
    ExtractedListPresence,
    ExtractedHHRec,
    ExtractedFunctionalUse,
    DataGroup,
    DataSource,
    Script,
    GroupType,
    DataDocument,
    DocumentType,
    PUCTag,
    Product,
    PUC,
    ProductDocument,
    UnitType,
    WeightFractionType,
    ExtractedHabitsAndPracticesDataType,
    PUCKind,
)

fixtures_standard = [
    "00_superuser",
    "01_lookups",
    "02_datasource",
    "03_datagroup",
    "04_PUC",
    "05_product",
    "06_datadocument",
    "07_extractedtext",
    "07b_extractedcpcat",
    "07c_extractedhhdoc",
    "07d_rawchem",
    "07e_extractedcomposition",
    "07f_extractedfunctionaluse",
    "07g_extractedlistpresence",
    "07h_extractedhhrec",
    "08_script",
    "09_productdocument",
    "10_habits_and_practices",
    "11_habits_and_practices_to_puc",
    # "12_product_to_puc",
    "13_puc_tag",
    "14_list_presence_tag",
    "15_list_presence_to_tag",
    "17_taxonomy",
    "18_functional_use",
]


def load_producttopuc():
    ProductToPUCFactory.create(
        product_id=878, puc_id=245, classification_method_id="MA"
    )
    ProductToPUCFactory.create(product_id=11, puc_id=1, classification_method_id="MA")
    ProductToPUCFactory.create(
        product_id=1861, puc_id=169, classification_method_id="MA"
    )
    ProductToPUCFactory.create(
        product_id=1868, puc_id=210, classification_method_id="MA"
    )
    ProductToPUCFactory.create(
        product_id=1862, puc_id=185, classification_method_id="MA"
    )
    ProductToPUCFactory.create(
        product_id=1854, puc_id=185, classification_method_id="MA"
    )
    ProductToPUCFactory.create(
        product_id=1865, puc_id=137, classification_method_id="MA"
    )
    ProductToPUCFactory.create(
        product_id=1870, puc_id=197, classification_method_id="MA"
    )
    ProductToPUCFactory.create(
        product_id=1866, puc_id=185, classification_method_id="MA"
    )
    ProductToPUCFactory.create(
        product_id=1859, puc_id=137, classification_method_id="MA"
    )
    ProductToPUCFactory.create(
        product_id=1842, puc_id=48, classification_method_id="MA"
    )
    ProductToPUCFactory.create(
        product_id=1867, puc_id=145, classification_method_id="MA"
    )
    ProductToPUCFactory.create(
        product_id=1866, puc_id=310, classification_method_id="MB"
    )
    ProductToPUCFactory.create(
        product_id=1866, puc_id=311, classification_method_id="BA"
    )
    ProductToPUCFactory.create(
        product_id=1866, puc_id=312, classification_method_id="AU"
    )
    ProductToPUCFactory.create(
        product_id=1924, puc_id=318, classification_method_id="AU"
    )
    return


fixtures_habits_practices = [
    "00_superuser",
    "01_lookups",
    "02_datasource",
    "03_datagroup",
    "04_PUC",
    "05_product",
    "06_datadocument",
    "07_extractedtext",
    "07d_rawchem",
    "07e_extractedcomposition",
    "08_script",
    "09_productdocument",
    "10_habits_and_practices",
    "11_habits_and_practices_to_puc",
]

datadocument_models = {
    "CO": ExtractedComposition,
    "FU": ExtractedFunctionalUse,
    "HP": ExtractedHabitsAndPractices,
    "CP": ExtractedListPresence,
    "HH": ExtractedHHRec,
}


class dotdict(dict):
    """dot.notation access to dictionary attributes"""

    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def load_browser():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    if settings.TEST_BROWSER == "firefox":
        return webdriver.Firefox()
    else:
        return webdriver.Chrome(
            executable_path=settings.CHROMEDRIVER_PATH, chrome_options=chrome_options
        )


def load_model_objects():
    user = User.objects.create_user(username="Karyn", password="specialP@55word")
    superuser = User.objects.create_superuser(
        username="SuperKaryn", password="specialP@55word", email="me@epa.gov"
    )
    ds = DataSource.objects.create(
        title="Data Source for Test", estimated_records=2, state="AT", priority="HI"
    )
    script = Script.objects.create(
        title="Test Download Script",
        url="http://www.epa.gov/",
        qa_begun=False,
        script_type="DL",
    )
    exscript = Script.objects.create(
        title="Test Extraction Script",
        url="http://www.epa.gov/",
        qa_begun=False,
        script_type="EX",
    )
    gt = GroupType.objects.create(title="Composition", code="CO")
    gt_hh = GroupType.objects.create(title="HHE Report", code="HH")
    dg = DataGroup.objects.create(
        name="Data Group for Test",
        description="Testing...",
        data_source=ds,
        download_script=script,
        downloaded_by=user,
        downloaded_at=timezone.now(),
        group_type=gt,
        url="https://www.epa.gov",
    )
    dg_hh = DataGroup.objects.create(
        name="HH Data Group for Test",
        description="HH Testing...",
        data_source=ds,
        download_script=script,
        downloaded_by=user,
        downloaded_at=timezone.now(),
        group_type=gt_hh,
        url="https://www.epa.gov",
    )
    dt = DocumentType.objects.create(title="MSDS", code="MS")
    dt2 = DocumentType.objects.create(title="HHE Report", code="HH")

    doc = DataDocument.objects.create(
        title="test document", data_group=dg, document_type=dt, filename="example.pdf"
    )
    p = Product.objects.create(upc="Test UPC for ProductToPUC")

    puc = PUC.objects.create(
        gen_cat="Test General Category",
        prod_fam="Test Product Family",
        prod_type="Test Product Type",
        description="Test Product Description",
        last_edited_by=user,
        kind=PUCKind.objects.get_or_create(name="Formulation", code="FO")[0],
    )

    extext = ExtractedText.objects.create(
        prod_name="Test Extracted Text Record",
        data_document=doc,
        extraction_script=exscript,
    )
    ut = UnitType.objects.create(title="percent composition")
    wft = WeightFractionType.objects.create(title="reported", description="reported")
    ec = ExtractedComposition.objects.create(
        extracted_text=extext,
        unit_type=ut,
        weight_fraction_type=wft,
        raw_chem_name="Test Chem Name",
        raw_cas="test_cas",
        lower_wf_analysis=0.123456789012345,
        central_wf_analysis=0.2,
        upper_wf_analysis=1,
        script=script,
    )
    rc = ec.rawchem_ptr

    pt = PUCTag.objects.create(
        name="Test PUC Attribute", definition="I'd really like to be defined."
    )
    pd = ProductDocument.objects.create(product=p, document=doc)
    ehp_dt = ExtractedHabitsAndPracticesDataType.objects.create(
        title="Test Data Type", description="Test Description"
    )
    ehp = ExtractedHabitsAndPractices.objects.create(
        extracted_text=extext,
        product_surveyed="Test Product Surveyed",
        data_type=ehp_dt,
    )

    return dotdict(
        {
            "user": user,
            "superuser": superuser,
            "ds": ds,
            "script": script,
            "exscript": exscript,
            "dg": dg,
            "dg_hh": dg_hh,
            "doc": doc,
            "p": p,
            "puc": puc,
            "extext": extext,
            "ut": ut,
            "wft": wft,
            "rc": rc,
            "ec": ec,
            "pt": pt,
            "pd": pd,
            "dt": dt,
            "gt": gt,
            "ehp_dt": ehp_dt,
            "ehp": ehp,
        }
    )
