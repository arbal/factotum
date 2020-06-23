{
  app: 'dashboard',
  type: 'composition',
  description: |||
    Service providing all Composition data in ChemExpoDB.
  |||,
  filters: ["chemical", "document", "category", "rid", "sid"],
  attributes: {
    rid: {
      type: 'string',
      description: "RID of the composition record.",
    },
    component: {
      type: 'string',
      description: |||
        Subcategory grouping chemical information on the document (may
        or may not be populated). Used when the document provides information on
        chemical make-up of multiple components or portions of a product (e.g. a
        hair care set (product) which contains a bottle of shampoo (component 1)
        and bottle of body wash (component 2)).
      |||,
    },
    lower_weight_fraction: {
      type: 'string',
      description: |||
        Lower bound of weight fraction for the chemical substance in the
        product, if provided on the document. If weight fraction is provided as a range,
        lower and upper values are populated. Values range from 0-1.
      |||,
    },
    central_weight_fraction: {
      type: 'string',
      description: |||
        Central value for weight fraction for the chemical substance in the
        product, if provided on the document. If weight fraction is provided as a point
        estimate, the central value is populated. Values range from 0-1.
      |||,
    },
    upper_weight_fraction: {
      type: 'string',
      description: |||
        Upper bound of weight fraction for the chemical substance in the product,
        if provided on the document. If weight fraction is provided as a range, lower and
        upper values are populated. Values range from 0-1.
      |||,
    },
    ingredient_rank: {
      type: 'string',
      description: "Rank of the chemical in the ingredient list or document.",
    },
  },
  relationships: [
    {
        object: import 'chemical.libsonnet',
    },
    {
        object: import 'dataDocument.libsonnet'
    },
    {
        object: import 'product.libsonnet',
        many: true,
    },
  ],
  errors: [
  ],
}
