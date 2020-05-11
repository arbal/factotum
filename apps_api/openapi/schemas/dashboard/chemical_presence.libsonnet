{
  app: 'dashboard',
  type: 'chemicalpresence',
  description: |||
    Service providing a list of all chemical presence tags in ChemExpoDB.
    A 'tag' (or keyword) may be applied to a chemical, indicating that there
    exists data in ChemExpoDB providing evidence that a chemical is related to
    that tag. Multiple tags may be applied to a single source-chemical instance,
    in which case the tags should be interpreted as a group.
  |||,
  attributes: {
    name: {
      type: 'string',
      description: "A 'tag' (or keyword) which may be applied to a chemical, indicating that there exists data in ChemExpoDB providing evidence that a chemical is related to that tag."
    },
    definition: {
      type: 'string',
      description: "Definition or description of the chemical presence tag."
    },
    kind: {
      type: 'string',
      description: "A means by which tags can be grouped, e.g. 'general use' tags vs. 'pharmaceutical' tags.",
    }
  },
  errors: [
  ],
}
