# OpenAPI Specification Generation

The OpenAPI specification is generated via [jsonnet](https://jsonnet.org/).

At the root of this directory are two files:
- `jsonapi.libsonnet`: This is core generator logic of the schema.
- `schema.jsonnet`: The top-level input for the schema.

There are also directories. Each directory represents a chemreg application. Within each application directory are definition files.

## Writing a definition file

A definition file is a representation of an OpenAPI schema. It includes some features of OpenAPI specification, but also some extra features that are documented below. Since this is a jsonnet file, you are free to use any jsonnet features you'd like. However, since jsonnet is a superset of JSON, it can just be a JSON object as well.

```jsonnet
{
    app: "The name of the application this schema is included under. It should be the same for each schema in the application directory. This is used to group together endpoints in the documentation.",
    type: "The schema type. This is usually a camelCase version of the model the schema represents.",
    pluralType: "Optional. The plural version of the schema type.",
    description: "A description of the schema.",
    attributes: {
        attributeName: {
            // all of https://swagger.io/docs/specification/data-models/keywords/
            oneOfGroup: "Optional. If this attribute should not be combined in a POST with another attribute, assign both attributes the same oneOfGroup. You should probably set `writeOnly` on grouped attributes, since this also works to group of responses as well as requests.",
            required: "Defaults to true unless a `default` is provided. Set to `false` if the attribute isn't required."
        }
    },
    relationships: [
        {
            object: "The definition of the related model. You'll need to `import` it above the definition.",
            many: "Defaults to `false`. Whether this is a one-to-many relationship or not.",
            default: "Optional. The ID of the object that this relationship defaults to being related to."
        }
    ],
    errors: [
        {
            status: "The integer representing the status code response.",
            detail: "The detail error message.",
            pointer: "The JSON pointer to where the error occurs.",
            code: "The error code."
        }
    ]
}
```

## Adding the definition file to the schema

You need to let jsonnet know of the new definition file once you've written a new one. In `schemas.jsonnet`, import the new definition and add it to the list of objects `objs`.
