import datetime
from haystack import indexes
from dashboard.models import Product, DataDocument, PUC, ProductToPUC, ExtractedChemical, DSSToxSubstance


class ExtractedChemicalIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.EdgeNgramField(
        document=True, use_template=True,
        template_name = 'search/indexes/dashboard/extractedchemical_text.txt')
    title=indexes.EdgeNgramField(model_attr='raw_chem_name', null=True)
    facet_model_name = indexes.CharField(faceted=True)
    result_css_class = indexes.CharField()

    raw_chem_name = indexes.EdgeNgramField(model_attr='raw_chem_name', null=True)

    raw_cas = indexes.CharField(model_attr='raw_cas', null=True)

    extracted_text_id = indexes.CharField(model_attr='extracted_text_id', null=False)

    data_document_id = indexes.CharField(model_attr='extracted_text__data_document_id', null=False)

    def get_model(self):
        return ExtractedChemical

    def prepare_facet_model_name(self, obj):
        return "Extracted Chemical"

    def prepare_result_css_class(self, obj):
        return "exchem-result"

    def index_queryset(self, using=None):
        """Used when the entire index for model is updated."""
        return self.get_model().objects.all()


class DSSToxSubstanceIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.EdgeNgramField(
        document=True, use_template=True,
        template_name = 'search/indexes/dashboard/dsstox_substance_text.txt')
    title=indexes.EdgeNgramField(model_attr='true_chemname')
    facet_model_name = indexes.CharField(faceted=True)
    result_css_class = indexes.CharField()
    true_chemname = indexes.EdgeNgramField(model_attr='true_chemname', null=True)
    true_cas = indexes.CharField(model_attr='true_cas', null=True)
    extracted_text_id = indexes.CharField(model_attr='extracted_chemical__extracted_text_id', null=False)
    data_document_id = indexes.CharField(model_attr='extracted_chemical__extracted_text__data_document_id', null=False)

    def get_model(self):
        return DSSToxSubstance

    def prepare_facet_model_name(self, obj):
        return "DSSTox Substance"

    def prepare_result_css_class(self, obj):
        return "dsstox-result"

    def index_queryset(self, using=None):
        """Used when the entire index for model is updated."""
        return self.get_model().objects.all()


class ProductIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.EdgeNgramField(
    document=True, use_template=True,
    template_name='search/indexes/dashboard/product_text.txt')
    title = indexes.EdgeNgramField(model_attr='title')
    facet_model_name = indexes.CharField(faceted=True)
    upc = indexes.CharField(model_attr='upc')
    result_css_class = indexes.CharField()
    short_description = indexes.EdgeNgramField(model_attr="short_description", null=True)

    brand_name = indexes.CharField(
        model_attr='brand_name',
        faceted=True,
        null=True)

    pucs = indexes.MultiValueField(
        stored=True,
        faceted=True,
        null=True)

    def prepare_pucs(self, obj):
        puc = obj.puc_set.first()
        if puc:
            if puc.prod_type:
                return (puc.prod_type, '096192')
            if puc.prod_fam:
                return (puc.prod_fam, '1171ba')
            if puc.gen_cat:
                return (puc.gen_cat, '1399c6')
        else:
            return ('None','d9534f')

    def get_model(self):
        return Product

    def index_queryset(self, using=None):
        """Used when the entire index for model is updated."""
        return self.get_model().objects.all()

    def prepare_facet_model_name(self, obj):
        return "Product"

    def prepare_result_css_class(self, obj):
        return "product-result"

class DataDocumentIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.EdgeNgramField(
    document=True, use_template=True,
    template_name='search/indexes/dashboard/data_document_text.txt')
    title            = indexes.EdgeNgramField(model_attr='title')
    facet_model_name = indexes.CharField(faceted=True)
    group_type       = indexes.CharField(faceted=True,
                                            model_attr='data_group__group_type')
    created_at      = indexes.DateTimeField(model_attr='created_at', null=True)
    result_css_class = indexes.CharField()

    filename = indexes.CharField(model_attr="filename", null=True)

    def prepare_facet_model_name(self, obj):
        return "Data Document"

    def prepare_result_css_class(self, obj):
        return "datadocument-result"

    def get_model(self):
        return DataDocument

    def index_queryset(self, using=None):
        """Used when the entire index for model is updated."""
        return self.get_model().objects.all()
