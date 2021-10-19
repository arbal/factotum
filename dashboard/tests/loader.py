from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from dashboard.models import (
    ExtractedText,
    ExtractedComposition,
    ExtractedHabitsAndPractices,
    ExtractedListPresence,
    ExtractedHPDoc,
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
    "07i_extractedhpdoc",
    "07j_extractedlmdoc",
    "07k_extractedlmrec",
    "08_script",
    "09_productdocument",
    "10_habits_and_practices",
    "11_habits_and_practices_to_puc",
    "12_product_to_puc",
    "13_puc_tag",
    "14_list_presence_tag",
    "15_list_presence_to_tag",
    "17_taxonomy",
    "18_functional_use",
    "19_curation_step",
]

fixtures_habits_practices = [
    "00_superuser",
    "01_lookups",
    "02_datasource",
    "03_datagroup",
    "04_PUC",
    "05_product",
    "06_datadocument",
    "07_extractedtext",
    "07i_extractedhpdoc",
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
            executable_path=settings.CHROMEDRIVER_PATH, options=chrome_options
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
    exscript2 = Script.objects.create(
        title="Manual (dummy)",
        url="http://www.epa.gov/",
        qa_begun=False,
        script_type="EX",
    )
    gt = GroupType.objects.create(title="Composition", code="CO")
    gt_hh = GroupType.objects.create(title="HHE Report", code="HH")
    gt_hp = GroupType.objects.create(title="Habits and practices", code="HP")
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
    dg_hp = DataGroup.objects.create(
        name="HP Data Group for Test",
        description="HP Testing...",
        data_source=ds,
        download_script=script,
        downloaded_by=user,
        downloaded_at=timezone.now(),
        group_type=gt_hp,
        url="https://www.epa.gov",
    )
    dt_ms = DocumentType.objects.create(title="MSDS", code="MS")
    dt_hh = DocumentType.objects.create(title="HHE Report", code="HH")
    dt_ja = DocumentType.objects.create(title="Journal article", code="JA")

    doc = DataDocument.objects.create(
        title="test document",
        data_group=dg,
        document_type=dt_ms,
        filename="example.pdf",
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
        cleaning_script=script,
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
    )
    rc = ec.rawchem_ptr

    pt = PUCTag.objects.create(
        name="Test PUC Attribute", definition="I'd really like to be defined."
    )
    pd = ProductDocument.objects.create(product=p, document=doc)
    ehpdt = ExtractedHabitsAndPracticesDataType.objects.create(
        title="Test Data Type", description="Test Description"
    )

    dd_hp = DataDocument.objects.create(
        title="Habits and Practices Document",
        data_group=dg_hp,
        document_type=dt_ja,
        filename="HPexample.pdf",
    )
    hpdoc = ExtractedHPDoc.objects.create(
        prod_name="Habits and practices prod name",
        data_document=dd_hp,
        extraction_script=exscript2,
    )
    ehp = ExtractedHabitsAndPractices.objects.create(
        extracted_text=hpdoc, product_surveyed="Test Product Surveyed", data_type=ehpdt
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
            "dd_hp": dd_hp,
            "hpdoc": hpdoc,
            "p": p,
            "puc": puc,
            "extext": extext,
            "ut": ut,
            "wft": wft,
            "rc": rc,
            "ec": ec,
            "pt": pt,
            "pd": pd,
            "dt": dt_ms,
            "ehpdt": ehpdt,
            "gt": gt,
            "gt_hp": gt_hp,
            "ehp": ehp,
        }
    )
