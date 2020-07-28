from rest_framework_json_api import serializers
from rest_framework_json_api.relations import (
    ResourceRelatedField,
    SerializerMethodResourceRelatedField,
)

from apps_api.core.jsonapi_fixes import ModelSerializer
from dashboard import models


class Base64ImageField(serializers.ImageField):
    """
    Field serializer from https://stackoverflow.com/a/28036805

    A Django REST framework field for handling image-uploads through raw post data.
    It uses base64 for encoding and decoding the contents of the file.

    Heavily based on
    https://github.com/tomchristie/django-rest-framework/pull/1268

    Updated for Django REST framework 3.

    """

    def to_internal_value(self, data):
        from django.core.files.base import ContentFile
        import base64
        import six
        import uuid

        # Check if this is a base64 string
        if isinstance(data, six.string_types):
            # Check if the base64 string is in the "data:" format
            if "data:" in data and ";base64," in data:
                # Break out the header from the base64 content
                header, data = data.split(";base64,")

            # Try to decode the file. Return validation error if it fails.
            try:
                decoded_file = base64.b64decode(data)
            except TypeError:
                self.fail("invalid_image")

            # Generate file name:
            file_name = str(uuid.uuid4())[:12]  # 12 characters are more than enough.
            # Get the file name extension:
            file_extension = self.get_file_extension(file_name, decoded_file)

            complete_file_name = "%s.%s" % (file_name, file_extension)

            data = ContentFile(decoded_file, name=complete_file_name)

        return super(Base64ImageField, self).to_internal_value(data)

    def get_file_extension(self, file_name, decoded_file):
        import imghdr

        extension = imghdr.what(file_name, decoded_file)
        extension = "jpg" if extension == "jpeg" else extension

        return extension

    def to_representation(self, value):
        """This is overridden as the server that hosts the image is not the same
        as the api server.  The media base url could be prepended but for now we are
        trusting the user to to this."""
        return value.url if value else None


class PUCSerializer(ModelSerializer):
    kind = serializers.CharField(
        required=True,
        max_length=2,
        source="kind.name",
        label="Kind",
        help_text="A means by which PUCs can be grouped, e.g. 'Formulation' PUCs vs. 'Article' PUCs.",
    )

    class Meta:
        model = models.PUC
        fields = [
            "id",
            "level_1_category",
            "level_2_category",
            "level_3_category",
            "definition",
            "kind",
            "url",
        ]
        extra_kwargs = {
            "id": {
                "help_text": "The unique numeric identifier for the PUC, \
                    used to cross-reference data obtained from other Factotum APIs.",
                "label": "PUC ID",
            },
            "level_1_category": {
                "help_text": "High-level product sector, such as personal care products or vehicle-related products.",
                "label": "Level 1 Category",
                "source": "gen_cat",
            },
            "level_2_category": {
                "help_text": "Unique product families under each of the product sectors.",
                "label": "Level 2 Category",
                "source": "prod_fam",
            },
            "level_3_category": {
                "help_text": "Specific product types in a product family.",
                "label": "Level 3 Category",
                "source": "prod_type",
            },
            "definition": {
                "help_text": "Definition or description of products that may be assigned to the PUC.",
                "label": "Definition",
                "source": "description",
            },
            "kind": {
                "help_text": "A means by which PUCs can be grouped, e.g. 'formulations' are PUCs related to consumer  \
                    product formulations (e.g. laundry detergent, shampoo, paint). 'Articles' are PUCs related to \
                    durable goods, or consumer articles (e.g. couches, children's play equipment).",
                "label": "Kind",
            },
        }


class ChemicalSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.DSSToxLookup
        fields = ["sid", "name", "cas", "url"]
        extra_kwargs = {
            "sid": {
                "help_text": "The DSSTox Substance Identifier, a unique identifier associated with a chemical substance.",
                "label": "DTXSID",
            },
            "name": {
                "help_text": "Preferred name for the chemical substance.",
                "label": "Preferred name",
                "source": "true_chemname",
            },
            "cas": {
                "help_text": "Preferred CAS number for the chemical substance.",
                "label": "Preferred CAS",
                "source": "true_cas",
            },
        }


class ProductSerializer(ModelSerializer):
    included_serializers = {
        "puc": PUCSerializer,
        "dataDocuments": "apps_api.api.serializers.DocumentSerializer",
    }

    url = serializers.HyperlinkedIdentityField(view_name="product-detail")
    puc = SerializerMethodResourceRelatedField(
        source="get_uberpuc",
        model=models.PUC,
        read_only=True,
        label="PUC with the highest confidence value",
        help_text=" Unique numeric identifier for the product use category assigned to the product \
        (if one has been assigned). Use the PUCs API to obtain additional information on the PUC.",
        related_link_view_name="product-related",
    )
    image = Base64ImageField(max_length=None, use_url=True)
    dataDocuments = ResourceRelatedField(
        source="documents",
        # read_only=True,
        queryset=models.DataDocument.objects,
        many=True,
        label="Document ID",
        help_text="Unique numeric identifier for the original data document associated with \
            the product. Use the Documents API to obtain additional information on the document.",
        related_link_view_name="product-related",
    )

    def get_uberpuc(self, obj):
        try:
            obj = obj.uber_puc
        except AttributeError:
            obj = None
        return obj

    class Meta:
        model = models.Product
        fields = [
            "id",
            "name",
            "upc",
            "manufacturer",
            "brand",
            "puc",
            "dataDocuments",
            "url",
            "size",
            "color",
            "short_description",
            "long_description",
            "epa_reg_number",
            "thumb_image",
            "medium_image",
            "large_image",
            "model_number",
            "image",
        ]
        extra_kwargs = {
            "id": {
                "label": "Product ID",
                "help_text": "The unique numeric identifier for the product, \
            used to cross-reference data obtained from other Factotum APIs.",
            },
            "name": {
                "label": "Name",
                "help_text": "Name of the product.",
                "source": "title",
            },
            "upc": {
                "label": "UPC",
                "help_text": "The Universal Product Code, \
        or unique numeric code used for scanning items at the point-of-sale. \
            UPC may be represented as 'stub#' if the UPC for the product is \
            not known.",
            },
            "manufacturer": {
                "label": "Manufacturer",
                "help_text": "Manufacturer of the product, if known.",
            },
            "brand": {
                "label": "Brand",
                "source": "brand_name",
                "help_text": "Brand name for the product, if known. May be the same as the manufacturer.",
            },
        }


class RawChemSerializer(ModelSerializer):
    included_serializers = {
        "chemical": "apps_api.api.serializers.ChemicalSerializer",
        "dataDocument": "apps_api.api.serializers.DocumentSerializer",
        "products": "apps_api.api.serializers.ProductSerializer",
    }

    chemical = SerializerMethodResourceRelatedField(
        source="dsstox",
        read_only=True,
        model=models.DSSToxLookup,
        related_link_view_name="chemicalInstance-related",
        self_link_view_name="chemicalInstance-relationships",
    )

    # related_link_view_name breaks when using the polymorphic serializer
    dataDocument = SerializerMethodResourceRelatedField(
        source="get_document",
        model=models.DataDocument,
        allow_null=True,
        required=False,
        read_only=True,
        # related_link_view_name="chemicalInstance-related",
        self_link_view_name="chemicalInstance-relationships",
    )

    # related_link_view_name breaks when using the polymorphic serializer
    products = SerializerMethodResourceRelatedField(
        source="get_products",
        model=models.Product,
        read_only=True,
        many=True,
        # related_link_view_name="chemicalInstance-related",
        self_link_view_name="chemicalInstance-relationships",
    )

    def get_document(self, obj):
        try:
            doc = obj.extracted_text.data_document
        except AttributeError:
            doc = None
        return doc

    def get_products(self, obj):
        try:
            queryset = obj.extracted_text.data_document.products.all()
        except AttributeError:
            queryset = []
        return queryset

    class Meta:
        model = models.RawChem
        fields = ["name", "cas", "rid", "chemical", "products", "dataDocument"]
        extra_kwargs = {
            "name": {"label": "Raw Chemical Name", "source": "raw_chem_name"},
            "cas": {"label": "Raw CAS", "source": "raw_cas"},
        }


class ExtractedChemicalSerializer(RawChemSerializer):
    chemical = SerializerMethodResourceRelatedField(
        source="dsstox",
        read_only=True,
        model=models.DSSToxLookup,
        related_link_view_name="composition-related",
        self_link_view_name="composition-relationships",
    )

    dataDocument = SerializerMethodResourceRelatedField(
        source="get_document",
        model=models.DataDocument,
        allow_null=True,
        required=False,
        read_only=True,
        related_link_view_name="composition-related",
        self_link_view_name="composition-relationships",
    )

    products = SerializerMethodResourceRelatedField(
        source="get_products",
        model=models.Product,
        read_only=True,
        many=True,
        related_link_view_name="composition-related",
        self_link_view_name="composition-relationships",
    )

    class Meta:
        model = models.ExtractedChemical
        fields = [
            "chemical",
            "dataDocument",
            "products",
            "rid",
            "component",
            "lower_weight_fraction",
            "central_weight_fraction",
            "upper_weight_fraction",
            "ingredient_rank",
            "url",
        ]
        extra_kwargs = {
            "component": {
                "label": "Component",
                "help_text": "Subcategory grouping chemical information on the document (may \
                    or may not be populated). Used when the document provides information on \
                    chemical make-up of multiple components or portions of a product (e.g. a \
                    hair care set (product) which contains a bottle of shampoo (component 1) \
                    and bottle of body wash (component 2)).",
            },
            "lower_weight_fraction": {
                "label": "Weight fraction - lower",
                "help_text": "Lower bound of weight fraction for the chemical substance in the \
                    product, if provided on the document. If weight fraction is provided as a range, \
                    lower and upper values are populated. Values range from 0-1.",
                "source": "lower_wf_analysis",
            },
            "central_weight_fraction": {
                "label": "Weight fraction - central",
                "help_text": "Central value for weight fraction for the chemical substance in the \
                    product, if provided on the document. If weight fraction is provided as a point \
                    estimate, the central value is populated. Values range from 0-1.",
                "source": "central_wf_analysis",
            },
            "upper_weight_fraction": {
                "label": "Weight fraction - upper",
                "help_text": "Upper bound of weight fraction for the chemical substance in the product,\
                 if provided on the document. If weight fraction is provided as a range, lower and \
                 upper values are populated. Values range from 0-1.",
                "source": "upper_wf_analysis",
            },
            "ingredient_rank": {
                "label": "Ingredient rank",
                "help_text": "Rank of the chemical in the ingredient list or document.",
            },
            "url": {"view_name": "composition-detail"},
        }


class ExtractedListPresenceSerializer(RawChemSerializer):
    class Meta:
        model = models.ExtractedListPresence
        fields = ["name", "cas", "rid", "chemical", "products", "dataDocument"]
        extra_kwargs = {
            "name": {"label": "Raw Chemical Name", "source": "raw_chem_name"},
            "cas": {"label": "Raw CAS", "source": "raw_cas"},
        }


class ExtractedHHRecSerializer(RawChemSerializer):
    class Meta:
        model = models.ExtractedHHRec
        fields = ["name", "cas", "rid", "chemical", "products", "dataDocument"]
        extra_kwargs = {
            "name": {"label": "Raw Chemical Name", "source": "raw_chem_name"},
            "cas": {"label": "Raw CAS", "source": "raw_cas"},
        }


class ExtractedFunctionalUseSerializer(RawChemSerializer):
    class Meta:
        model = models.ExtractedFunctionalUse
        fields = ["name", "cas", "rid", "chemical", "products", "dataDocument"]
        extra_kwargs = {
            "name": {"label": "Raw Chemical Name", "source": "raw_chem_name"},
            "cas": {"label": "Raw CAS", "source": "raw_cas"},
        }


class ChemicalInstancePolymorphicSerializer(serializers.PolymorphicModelSerializer):
    polymorphic_serializers = [
        ExtractedChemicalSerializer,
        ExtractedListPresenceSerializer,
        ExtractedHHRecSerializer,
        ExtractedFunctionalUseSerializer,
        RawChemSerializer,
    ]

    # These are never actually evaluated but are needed for the include validation checks
    # data_document is required as the PolymorphicModelSerializer is built on
    # ModelSerializer which uses the original version of IncludedResourcesValidationMixin
    included_serializers = {
        "chemical": "apps_api.api.serializers.ChemicalSerializer",
        "data_document": "apps_api.api.serializers.DocumentSerializer",
        "dataDocument": "apps_api.api.serializers.DocumentSerializer",
        "products": "apps_api.api.serializers.ProductSerializer",
    }

    class Meta:
        model = models.RawChem
        fields = []


class DataSourceSerializer(ModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dataSource-detail")

    source_url = serializers.CharField(
        source="url", read_only=True, allow_null=False, label="URL"
    )

    class Meta:
        model = models.DataSource
        fields = [
            "id",
            "title",
            "source_url",
            "description",
            "estimated_records",
            "state",
            "priority",
            "url",
        ]


class DataGroupSerializer(ModelSerializer):
    included_serializers = {"dataSource": DataSourceSerializer}

    url = serializers.HyperlinkedIdentityField(view_name="dataGroup-detail")

    group_type = serializers.CharField(
        source="group_type.title", read_only=True, allow_null=False, label="Group type"
    )

    group_type_code = serializers.CharField(
        source="group_type.code",
        read_only=True,
        allow_null=False,
        label="Group type code",
    )

    dataSource = ResourceRelatedField(
        label="Data Source",
        help_text="The Data Source associated with this data group",
        read_only=True,
        source="data_source",
        related_link_view_name="dataGroup-related",
        self_link_view_name="dataGroup-relationships",
    )

    class Meta:
        model = models.DataGroup
        fields = [
            "id",
            "name",
            "description",
            "downloaded_at",
            "group_type",
            "group_type_code",
            "dataSource",
            "url",
        ]


class DocumentSerializer(serializers.HyperlinkedModelSerializer):
    included_serializers = {
        "products": ProductSerializer,
        "dataGroup": DataGroupSerializer,
        "dataSource": DataSourceSerializer,
    }

    url = serializers.HyperlinkedIdentityField(view_name="dataDocument-detail")

    date = serializers.CharField(
        default=None,
        read_only=True,
        allow_null=True,
        max_length=25,
        source="extractedtext.doc_date",
        label="Date",
        help_text="Publication date for the document.",
    )

    data_type = serializers.CharField(
        source="data_group.group_type.title",
        read_only=True,
        allow_null=False,
        label="Data type",
        help_text="Type of data provided by the document, e.g. 'Composition' \
            indicates the document provides data on chemical composition of a consumer product.",
    )
    document_type = serializers.CharField(
        source="document_type.title",
        read_only=True,
        allow_null=False,
        label="Document type",
        help_text="Standardized description of the type of document (e.g. Safety Data Sheet (SDS), \
            product label, journal article, government report).",
    )
    document_url = serializers.SerializerMethodField(
        read_only=True,
        allow_null=True,
        label="URL",
        help_text="Link to a locally stored copy of the document.",
    )
    source_document_url = serializers.SerializerMethodField(
        read_only=True,
        allow_null=True,
        label="Source Document URL",
        help_text="Link to a remote copy of the document.",
    )
    products = ResourceRelatedField(
        label="Products",
        help_text="Products associated with the \
             original data document. May be >1 product associated with each document. \
             See the Products API for additional information on the product.",
        many=True,
        read_only=True,
        related_link_view_name="dataDocument-related",
        self_link_view_name="dataDocument-relationships",
    )

    chemicals = SerializerMethodResourceRelatedField(
        many=True,
        read_only=True,
        source="get_chemicals",
        model=models.RawChem,
        self_link_view_name="dataDocument-relationships",
    )

    dataGroup = ResourceRelatedField(
        label="Data Group",
        help_text="The Data Group associated with this document",
        read_only=True,
        source="data_group",
        related_link_view_name="dataDocument-related",
        self_link_view_name="dataDocument-relationships",
    )

    dataSource = SerializerMethodResourceRelatedField(
        read_only=True,
        source="data_group.data_source",
        model=models.DataSource,
        related_link_view_name="dataDocument-related",
        self_link_view_name="dataDocument-relationships",
    )

    def get_chemicals(self, obj):
        try:
            queryset = obj.extractedtext.rawchem.all()
        except AttributeError:
            queryset = []
        return queryset

    def get_document_url(self, obj) -> serializers.URLField:
        return obj.file.url if obj.file else None

    def get_source_document_url(self, obj) -> serializers.URLField:
        return obj.url

    class Meta:
        model = models.DataDocument
        fields = [
            "id",
            "title",
            "subtitle",
            "organization",
            "date",
            "dataGroup",
            "dataSource",
            "data_type",
            "document_type",
            "url",
            "notes",
            "products",
            "chemicals",
            "document_url",
            "source_document_url",
        ]
        extra_kwargs = {
            "id": {
                "label": "Document ID",
                "help_text": "The unique numeric identifier for the original data document providing data to ChemExpoDB.",
            },
            "title": {"label": "Title", "help_text": "Title of the document."},
            "subtitle": {
                "label": "Subtitle",
                "help_text": "Subtitle for the document. \
                May also be the heading/caption for the table from which data was extracted.",
            },
            "organization": {
                "label": "Organization",
                "help_text": "The organization which published the document. If the document is \
                    a peer-reviewed journal article, the name of the journal.",
            },
            "notes": {
                "label": "Notes",
                "source": "note",
                "help_text": "General notes about the data document, written by ChemExpoDB data curators.",
            },
        }


class ChemicalPresenceSerializer(ModelSerializer):
    kind = serializers.CharField(
        required=True,
        max_length=50,
        source="kind.name",
        label="Kind",
        help_text="A means by which tags can be grouped, e.g. 'general use' tags vs. 'pharmaceutical' tags.",
    )

    class Meta:
        model = models.ExtractedListPresenceTag
        # mark the type as chemicalpresence instead of ExtractedListPresenceTag to match the endpoint

        fields = ["name", "definition", "kind"]
        extra_kwargs = {
            "name": {
                "help_text": "A 'tag' (or keyword) which may be applied to a chemical, indicating that there exists data in ChemExpoDB providing evidence that a chemical is related to that tag.",
                "label": "Name",
            },
            "definition": {
                "help_text": "Definition or description of the chemical presence tag.",
                "label": "Definition",
            },
        }


class FunctionalUseCategorySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.FunctionalUseCategory
        fields = ["title", "description"]
        extra_kwargs = {
            "title": {
                "help_text": "Title of the functional use category.",
                "label": "Title",
            },
            "description": {
                "help_text": "Description of the functional use category.",
                "label": "Description",
            },
        }


class FunctionalUseSerializer(ModelSerializer):
    # The related view uses dataDocument but the include parameter parses to data_document
    #  Until this bug is fixed both includes will exist and point to the same location.
    included_serializers = {
        "chemical": ChemicalSerializer,
        "category": FunctionalUseCategorySerializer,
        "dataDocument": DocumentSerializer,
    }

    dataDocument = ResourceRelatedField(
        source="chem.extracted_text.data_document",
        model=models.DataDocument,
        read_only=True,
        related_link_view_name="functionalUse-related",
        self_link_view_name="functionalUse-relationships",
    )

    chemical = ResourceRelatedField(
        source="chem.dsstox",
        model=models.DSSToxLookup,
        allow_null=True,
        required=False,
        read_only=True,
        related_link_view_name="functionalUse-related",
        self_link_view_name="functionalUse-relationships",
    )

    rid = serializers.CharField(
        source="chem.rid",
        read_only=True,
        label="RID",
        help_text="The Chemical RID associated with this functional use record.",
    )

    class Meta:
        model = models.FunctionalUse
        fields = [
            "chemical",
            "rid",
            "category",
            "dataDocument",
            "report_funcuse",
            "clean_funcuse",
            "url",
        ]
        extra_kwargs = {
            "category": {
                "label": "Category",
                "help_text": "The Functional Use Category associated with this functional use record.",
                "related_link_view_name": "functionalUse-related",
                "self_link_view_name": "functionalUse-relationships",
            },
            "url": {"view_name": "functionalUse-detail"},
        }

    # class JSONAPIMeta:
    #     included_resources = ["chemical",]


class ExtractedListPresenceTagSerializer(ModelSerializer):
    name = serializers.CharField(label="Keyword Name", help_text="")

    class Meta:
        model = models.ExtractedListPresenceTag
        fields = ["name"]
        extra_kwargs = {
            "name": {
                "label": "Keyword Name",
                "help_text": "This is the name of a list presence keyword",
            }
        }


class TagsetRelatedDataSerializer(serializers.Serializer):
    document_id = serializers.CharField(
        source="extracted_text.data_document_id", label="Data Document ID", help_text=""
    )
    rids = serializers.SerializerMethodField(
        label="RID List", help_text="List presence rids."
    )

    def get_rids(self, obj):
        """If more information is needed this should be moved into its own serializer
        """
        return [obj.rid for obj in obj["extracted_list_presence"]]


class TagsetSerializer(serializers.Serializer):
    keywords = ExtractedListPresenceTagSerializer(many=True, source="tags")
    related = TagsetRelatedDataSerializer(many=True)


# TODO: When this is updated it should be based off of ExtractedListPresence
#  and should build on the ExtractedListPresenceSerializer.
class ChemicalPresenceTagsetSerializer(serializers.ModelSerializer):
    # Tagsets come from a partial function that are added through ChemicalPresenceTagsetFilter
    keyword_sets = TagsetSerializer(source="tagsets", many=True)

    class Meta:
        model = models.DSSToxLookup
        fields = ["chemical_id", "keyword_sets"]
        extra_kwargs = {"chemical_id": {"label": "DTXSID", "source": "sid"}}
