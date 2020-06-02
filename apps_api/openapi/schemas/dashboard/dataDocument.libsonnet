{
  app: 'dashboard',
  type: 'dataDocument',
  description: 'Service providing a list of all documents in ChemExpoDB, along with
    metadata describing the document. Service also provides the actual data
    points found in, and extracted from, the document. e.g., chemicals and their
    weight fractions may be included for composition documents.',
  readOnly: true,
  queryParams: [],
  attributes: {
    title: {
      type: 'string',
      description: 'Title of the data document'
    },
    subtitle: {
      type: 'string',
      description: 'Subtitle of the data document'
    },
    organization: {
      type: 'string',
      description: 'Organization that this data document is about'
    },
    date: {
      type: 'string',
      description: 'Date of publication for the data document'
    },
    data_type: {
      type: 'string',
      description: 'Type of data contained within the data document'
    },
    document_type: {
      type: 'string',
      description: 'Type of the data document'
    },
    url: {
      type: 'string',
      description: 'URL of the data document for download'
    },
    notes: {
      type: 'string',
      description: 'Miscellaneous information about the data document'
    },
  },
#  relationships: [
#    {
#      object: import 'chemical.libsonnet',
#    },
#    #{ object: import 'product.libsonnet' },
#  ],
  errors: [
  ],
}
