local dataDocument = import 'dataDocument.libsonnet';
{
  app: 'dashboard',
  type: 'product',
  allowed_methods: ['fetch', 'list', 'bulk', 'create'],
  description: |||
    list: Service providing a list of all products in ChemExpoDB, along with metadata
    describing the product. In ChemExpoDB, a product is defined as an item having a
    unique UPC. Thus the same formulation (i.e., same chemical composition) may be
    associated with multiple products, each having their own UPC (e.g., different size
    bottles of a specific laundry detergent all have the same chemical make-up, but
    have different UPCs).
  |||,
  filters: ["upc", "sid", "chemical"],
  attributes: {
    name: {
      type: 'string',
      description: 'Name of the product.'
    },
    upc: {
      type: 'string',
      description: |||
          The Universal Product Code,
          or unique numeric code used for scanning items at the point-of-sale.
          UPC may be represented as 'stub#' if the UPC for the product is
          not known.
        |||,
      required: false,
    },
    size: {
      type: 'string',
      required: false,
    },
    color: {
      type: 'string',
      required: false,
    },
    short_description: {
      type: 'string',
      required: false,
    },
    long_description: {
      type: 'string',
      required: false,
    },
    epa_reg_number: {
      type: 'string',
      required: false,
    },
    thumb_image: {
      type: 'string',
      description: "URL of the thumbnail sized image",
      required: false,
    },
    medium_image: {
      type: 'string',
      description: "URL of the medium size image",
      required: false,
    },
    large_image: {
      type: 'string',
      description: "URL of the full size image",
      required: false,
    },
    model_number: {
      type: 'string',
      required: false,
    },
    image: {
      type: 'base64 encoded file',
      required: false,
    },
    manufacturer: {
      type: 'string',
      description: 'Manufacturer of the product, if known.',
      required: false,
    },
    product_url: {
      type: 'string',
      description: 'This field corresponds to the "url" model field.',
      required: false,
    },
    brand: {
      type: 'string',
      description: 'Brand name for the product, if known. May be the same as the manufacturer.',
      required: false,
    },
  },
  relationships: [
    {
      object: {
        app: 'dashboard',
        type: 'dataDocument',
        typePlural: 'dataDocuments',
        hasRelationships: false,
        attributes: {
        },
      },
      many: true,
    },
    {
      object: {
        app: 'dashboard',
        type: 'productUberPuc',
        typePlural: 'productUberPuc',
        hasRelationships: false,
        attributes: {
        },
      },
      many: false,
      readOnly: true,
    },
  ],
  errors: [],
}
