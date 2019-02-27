import datetime
from haystack import indexes
from dashboard.models import Product, DataDocument, PUC, ProductToPUC, ExtractedChemical, DSSToxLookup, RawChem


class RawChemIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.EdgeNgramField(
        document=True, use_template=True,
        template_name = 'search/indexes/dashboard/extractedchemical_text.txt')
    title=indexes.EdgeNgramField(model_attr='raw_chem_name', null=True)
    facet_model_name = indexes.CharField(faceted=True)
    result_css_class = indexes.CharField()

    raw_chem_name = indexes.EdgeNgramField(model_attr='raw_chem_name', null=True)
    raw_cas = indexes.CharField(model_attr='raw_cas', null=True)

    sid = indexes.CharField(model_attr='dsstox__sid', null=True)
    true_cas = indexes.CharField(model_attr='dsstox__true_cas', null=True)
    true_chem_name = indexes.CharField(model_attr='dsstox__true_chemname', null=True)

    raw_chem_id = indexes.CharField(model_attr='id', null=False)

    data_document_id = indexes.CharField()

    def get_model(self):
        # TODO: should this use the subclass instead?
        return RawChem

    def prepare_data_document_id(self, obj):
        dd = obj.get_data_document()
        if dd:
            return dd.id
        else:
            return -1


    def prepare_facet_model_name(self, obj):
        # TODO: make this aware of the subclass
        return "Extracted Chemical"

    def prepare_result_css_class(self, obj):
        # TODO: make this aware of the subclass
        return "exchem-result"

    def index_queryset(self, using=None):
        """Used when the entire index for model is updated."""
        return self.get_model().objects.all()


class DSSToxIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.EdgeNgramField(
        document=True, use_template=True,
        template_name = 'search/indexes/dashboard/dsstox_lookup_text.txt')
    sid = indexes.CharField(model_attr='sid')
    title=indexes.EdgeNgramField(model_attr='true_chemname')
    facet_model_name = indexes.CharField(faceted=True)
    result_css_class = indexes.CharField()
    true_chemname = indexes.EdgeNgramField(model_attr='true_chemname', null=True)
    true_cas = indexes.CharField(model_attr='true_cas', null=True)

    def get_model(self):
        return DSSToxLookup

    def prepare_facet_model_name(self, obj):
        return "DSSTox Lookup"

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

