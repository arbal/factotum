{
  app: 'dashboard',
  type: 'puc',
  description: |||
    Service providing a list of all Product Use Categories (PUCs) in ChemExpoDB.
    The PUCs follow a three-tiered hierarchy (Levels 1-3) for categorizing products.
    Every combination of Level 1-3 categories is unique, and the combination of Level 1, Level 2,
    and Level 3 categories together define the PUCs. Additional information on PUCs can be found in
    Isaacs, 2020. https://www.nature.com/articles/s41370-019-0187-5
  |||,
  filters: ["chemical", "sid"],
  attributes: {
    "level_1_category": {
        "type": "string",
        "description": "High-level product sector, such as personal care products or vehicle-related products.",
    },
    "level_2_category": {
        "type": "string",
        "description": "Unique product families under each of the product sectors.",
    },
    "level_3_category": {
        "type": "string",
        "description": "Specific product types in a product family.",
    },
    "definition": {
        "type": "string",
        "description": "Definition or description of products that may be assigned to the PUC.",
    },
    "kind": {
        "type": "string",
        "description": |||
            A means by which PUCs can be grouped, e.g. 'formulations' are PUCs related to consumer
            product formulations (e.g. laundry detergent, shampoo, paint). 'Articles' are PUCs related to
            durable goods, or consumer articles (e.g. couches, children's play equipment).
        |||,
    },
  },
  relationships: [],
  errors: [],
}
