{
  app: 'dashboard',
  type: 'functionalUse',
  description: 'Service providing a list of all functional uses.',
  filters: ["chemical", "document", "category"],
  attributes: {
    rid: {
      type: 'string',
      description: 'Title of the functional use category.',
    },
    report_funcuse: {
      type: 'string',
      allowEmptyValue: true,
      description: "The reported functional use",
    },
  },
  relationships: [
    {
      object: import 'chemical.libsonnet'
    },
    {
      object: import 'dataDocument.libsonnet'
    },
    {
      object: import 'functionalUseCategory.libsonnet'
    },
  ],
  errors: [
  ],
}
