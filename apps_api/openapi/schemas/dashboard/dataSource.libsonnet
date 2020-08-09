{
  app: 'dashboard',
  type: 'dataSource',
  description: 'Service providing a list of all data sources.',
  attributes: {
    title: {
      type: 'string',
      description: 'Title of the data source.',
    },
    source_url: {
       type: 'string',
       allowEmptyValue: true,
       description: 'The url of the data source.',
    },
    description: {
       type: 'string',
       allowEmptyValue: true,
       description: 'Description of the data source.',
    },
    estimated_records: {
       type: 'integer',
       description: 'The estimated records count of the data source',
    },
    state: {
      type: 'string',
      description: 'The state of the data source. The choices are ["AT", "IP", "CO", "ST"].',
    },
    priority: {
      type: 'string',
      description: 'The priority of the data source. The choices are ["HI", "MD", "LO"].',
    },
  },
  errors: [
  ],
}
