{
  app: 'dashboard',
  type: 'dataGroup',
  description: 'Service providing a list of all data groups.',
  attributes: {
    name: {
      type: 'string',
      description: 'Name of the data group.',
    },
    description: {
       type: 'string',
       allowEmptyValue: true,
       description: 'Description of the data group.',
    },
    downloaded_at: {
       type: 'string',
       description: 'The downloaded time of the data group.',
    },
    group_type: {
      type: 'string',
      description: 'The group type title the data group is associated with.',
    },
    group_type_code: {
      type: 'string',
      description: 'The group type code the data group is associated with.',
    },
  },
  relationships: [
    {
      object: import 'dataSource.libsonnet'
    },
  ],
  errors: [
  ],
}
