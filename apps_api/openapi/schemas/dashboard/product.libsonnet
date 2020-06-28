{
  app: 'dashboard',
  type: 'product',
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
    },
    manufacturer: {
      type: 'string',
      description: 'Manufacturer of the product, if known.'
    },
    brand: {
      type: 'string',
      description: 'Brand name for the product, if known. May be the same as the manufacturer.'
    },
  },
  relationships: [],
  errors: [],
}
