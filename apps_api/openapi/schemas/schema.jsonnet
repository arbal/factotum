/////////////////////
// API description //
/////////////////////
local description = |||
  The Factotum Web Services API is a service that provides data about Product Usage Category (PUC), consumer products, and the chemicals related to PUCs and products.

  ### OpenAPI
  This documentation is generated via the [OpenAPI specification](https://swagger.io/specification/) downloadable above. You can use this specification to assist in developing apps and using the API. For example, [Postman can import the OpenAPI specification](https://learning.postman.com/docs/postman/collections/working-with-openAPI/) to automatically build collections.

  ### JSON:API
  Endpoints are being changed to follow the [JSON:API specification](https://jsonapi.org/).
|||;


///////////////////
// Import models //
///////////////////

local functional_use = import 'dashboard/functional_use.libsonnet';
local chemical_presence = import 'dashboard/chemical_presence.libsonnet';

////////////////////////
// List of all models //
////////////////////////
local objs = [
    chemical_presence,
    functional_use,
];

// Build spec
local jsonapi = import 'jsonapi.libsonnet';
jsonapi.buildSpec(objs, description)
