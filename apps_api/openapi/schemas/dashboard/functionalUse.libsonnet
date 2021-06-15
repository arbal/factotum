{
  app: 'dashboard',
  type: 'functionalUse',
  description: 'Service providing a list of all reported functional uses assigned to chemicals.',
  filters: ["chemical", "document", "category", "reported_funcuse"],
  attributes: {
    rid: {
      type: 'string',
      description: 'RID of the raw chemical record.',
    },
    report_funcuse: {
      type: 'string',
      allowEmptyValue: true,
      description: "The reported functional use assigned to the chemical.",
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
