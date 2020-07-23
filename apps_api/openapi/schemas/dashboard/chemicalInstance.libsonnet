{
  app: 'dashboard',
  type: 'chemicalInstance',
  allowed_methods: ['list'],
  description: |||
    Service providing all Chemical Records attached to Documents in the Human Exposure Database.
    This endpoint returns multiple types so the result type and attributes may be from a
    different resource.
  |||,
  filters: ["chemical", "sid", "rid", "rid.isnull"],
  attributes: {
    rid: {
      type: 'string',
      description: "RID of the composition record.",
    },
    name: {
      type: 'string',
      description: "The name of the chemical on the document.",
    },
    cas: {
      type: 'string',
      description: "The CAS of the chemical on the document",
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
