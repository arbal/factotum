{
  app: 'dashboard',
  type: 'chemical',
  description: 'Service providing a list of all registered chemical
    substances linked to data in ChemExpoDB. All chemical data in
    ChemExpoDB is linked by the DTXSID, or the unique structure based
    identifier for the chemical substance. Service provides the DTXSID,
    preferred chemical name, and preferred CAS.',
  queryParams: [],
  attributes: {
    sid: {
      type: 'string',
      description: 'The unique structure based identifier for the chemical substance.',
    },
    "name": {
      type: 'string',
      description: 'Preferred Name for the chemical substance.'
    },
    "cas": {
      type: 'string',
      description: 'Preferred CAS number for the chemical substance.'
    },
  },
  errors: [
  ],
}
