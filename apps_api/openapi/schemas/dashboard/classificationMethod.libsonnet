{
  app: 'dashboard',
  type: 'classificationMethod',
  typePlural: 'classificationMethods',
  description: 'Service providing a list of all classification methods when assign PUC to Product.',
  attributes: {
    code: {
          type: 'string',
          description: 'The unique code of the classification method.',
    },
    name: {
          type: 'string',
          description: 'The unique name of the classification method.',
    },
    rank: {
          type: 'integer',
          description: 'The unique rank of the classification method.',
    },
  },
  errors: [
  ],
}
