local utils = {
  _innerCartesianProduct(x_set, y_set)::
    if x_set == null then
      [[y] for y in y_set]
    else
      [x + [y] for x in x_set for y in y_set],
  cartesianProduct(sets)::
    if std.length(sets) > 0 then
      std.foldl(self._innerCartesianProduct, sets, null)
    else
      [],
};

local ModelTemplate = {
  app:: error 'Must set "app"',
  type:: error 'Must set "type"',
  allowed_methods:: ['fetch', 'list',],
  allowed_methods_set:: std.set(self.allowed_methods),
  description:: '',
  attributes:: error 'Must set "attributes"',
  typePlural:: self.type + 's',
  relationships:: [],
  errors:: [],
  filters:: [],
  hasRelationships:: std.length(self.relationships) > 0,
  hasFilters:: std.length(self.filters) > 0,
  defaultRelationships:: [relatedObj for relatedObj in self.relationships if relatedObj.default != null],
  allRelationshipsDefault:: std.length(self.defaultRelationships) == std.length(self.relationships),
  relatedTypes:: [relatedObj.object.type for relatedObj in self.relationships],
  allTypes:: std.set([self.type] + self.relatedTypes),
  readableAttributes(type)::
    if type == self.type then
      std.filter(
        (function(k) !self.attributes[k].writeOnly),
        std.objectFields(self.attributes)
      )
    else
      local obj = std.filter(
        (function(x) x.object.type == type),
        self.relationships
      )[0].object;
      std.filter(
        (function(k) !obj.attributes[k].writeOnly),
        std.objectFields(obj.attributes)
      ),
};

local AttributeTemplate(attributeObj) = {
  description: '',
  readOnly:: false,
  writeOnly:: false,
  oneOfGroup:: '',
  default:: null,
  required:: self.default == null,
  nullable: false,
  [if attributeObj.type == 'string' then 'minLength']: 1,
};

local RelationshipTemplate(modelObj) = {
  parent:: modelObj,
  object:: error 'Must set "relationships[x].object"',
  many:: false,
  default:: null,
  required:: self.default == null,
  readOnly:: false,
};

local BaseModelProcessor = {
  attributes+: {
    [attribute]: AttributeTemplate(super[attribute]) + super[attribute] + {
      readOnly:: super.readOnly,
      writeOnly:: super.writeOnly,
      oneOfGroup:: super.oneOfGroup,
      required:: super.required,
    }
    for attribute in std.objectFields(super.attributes)
  },
};

local RelationshipProcessor = {
  object: ModelTemplate + super.object + BaseModelProcessor,
};

local ModelProcessor = BaseModelProcessor {
  relationships: [

    RelationshipTemplate($) + relationship + RelationshipProcessor
    for relationship in super.relationships
  ],
};

local meta = {
  read:: {
    type: 'object',
    properties: {
      apiVersion: {
        type: 'string',
        enum: ['1.0.0-beta'],
        example: '1.0.0-beta',
        description: 'The factotum API version that served this response.',
      },
    },
    required: ['apiVersion'],
  },
  readList:: self.read {
    properties+: {
      pagination: {
        type: 'object',
        description: 'Information regarding pagination.',
        properties: {
          page: {
            type: 'integer',
            minimum: 1,
            description: 'The current page.',
            example: 3,
          },
          pages: {
            type: 'integer',
            minimum: 1,
            description: 'The total number of pages.',
            example: 5,
          },
          count: {
            type: 'integer',
            minimum: 0,
            maximum: 1000,
            description: 'The total number of objects in this page.',
            example: 100,
          },
        },
        required: ['page', 'pages', 'count'],
      },
    },
    required+: ['pagination'],
  },
};

local buildParameters(obj) = {
  id:: {
    name: 'id',
    'in': 'path',
    required: true,
    description: "The resource object's unique [identify](https://jsonapi.org/format/#document-resource-object-identification). It must locate a single, unique resource.",
    schema: {
      type: 'string',
      pattern: '\\d+',
    },
  },
  fields:: {
    name: 'fields[' + obj.type + ']',
    'in': 'query',
    description: '[sparse fieldsets](https://jsonapi.org/format/#fetching-sparse-fieldsets)',
    example: obj.readableAttributes(obj.type)[0],
    required: false,
    schema: {
      type: 'array',
      default: obj.readableAttributes(obj.type),
    },
  },
  filters:: [
      {
        name: 'filter[' + filter_name + ']',
        'in': 'query',
        description: '[filter](https://jsonapi.org/format/#fetching-filtering)',
        example: "value",
        required: false,
      } for filter_name in obj.filters
    ],
  page:: {
    name: 'page',
    'in': 'query',
    description: '[pagination](https://jsonapi.org/format/#fetching-pagination)',
    required: false,
    style: 'deepObject',
    example: { number: 3 },
    explode: true,
    schema: {
      type: 'object',
      properties: {
        size: {
          type: 'integer',
          description: 'The maximum number of resources to fetch in this request.',
          maximum: 1000,
          minimum: 1,
          default: 100,
        },
        number: {
          type: 'integer',
          description: 'The page number to fetch.',
          minimum: 1,
          default: 1,
        },
      },
    },
  },
  sort:: {
    name: 'sort',
    'in': 'query',
    description: '[list of fields to sort by](https://jsonapi.org/format/#fetching-sorting)',
    required: false,
    style: 'form',
    example: [obj.readableAttributes(obj.type)[0]],
    schema: {
      type: 'array',
      default: obj.readableAttributes(obj.type),
    },
  },
  write:: [self.id],
  read:: [self.id, self.fields],
  readList:: [self.sort, self.fields, self.page,] + [obj for obj in self.filters],
};

local responseCodeDescriptions = {
  '200': 'OK',
  '201': 'Created',
  '202': 'Accepted',
  '204': 'No Content',
  '400': 'Bad Request',
  '401': 'Unauthorized',
  '403': 'Forbidden',
  '404': 'Not Found',
  '405': 'Method Not Allowed',
  '406': 'Not Acceptable',
  '409': 'Conflict',
  '415': 'Unsupported Media Type',
  '429': 'Too Many Requests',
  '500': 'Server Error',
};

local buildErrors(obj) = {
  all:: [
    {
      status: 400,
      detail: 'Bad Request (400)',
    },
    {
      status: 400,
      detail: 'Malformed request.',
      code: 'parse_error',
    },
    {
      status: 400,
      detail: 'invalid query parameter: {query_parameter}',
      code: 'invalid',
    },
    {
      status: 401,
      detail: 'Incorrect authentication credentials.',
      code: 'authentication_failed',
    },
    {
      status: 403,
      detail: 'Authentication credentials were not provided.',
      code: 'not_authenticated',
    },
    {
      status: 403,
      detail: 'You do not have permission to perform this action.',
      code: 'permission_denied',
    },
    {
      status: 404,
      detail: 'Not found.',
      code: 'not_found',
    },
    {
      status: 405,
      detail: 'Method "{method}" not allowed.',
      code: 'method_not_allowed',
    },
    {
      status: 406,
      detail: 'Could not satisfy the request Accept header.',
      code: 'not_acceptable',
    },
    {
      status: 415,
      detail: 'Unsupported media type "{media_type}" in request.',
      code: 'unsupported_media_type',
    },
    {
      status: 429,
      detail: 'Request was throttled.',
      code: 'throttled',
    },
    {
      status: 500,
      detail: 'Server Error (500)',
      code: 'throttled',
    },
  ],
  buildObj(err):: {
    type: 'object',
    title: if std.objectHas(err, 'code') then err.code else 'generic',
    properties: {
      [if std.objectHas(err, 'detail') then 'detail']: {
        type: 'string',
        enum: [err.detail],
        description: 'A human-readable explanation specific to this occurrence of the problem.',
      },
      [if std.objectHas(err, 'code') then 'code']: {
        type: 'string',
        enum: [err.code],
        description: 'An application-specific error code.',
      },
      [if std.objectHas(err, 'status') then 'status']: {
        type: 'string',
        enum: ['%d' % err.status],
        description: 'The HTTP status code applicable to this problem.',
      },
      [if std.objectHas(err, 'pointer') then 'source']: {
        type: 'object',
        description: 'An object containing references to the source of the error',
        properties: {
          pointer: {
            type: 'string',
            description: 'A JSON Pointer to the associated entity in the request document.',
            enum: [err.pointer],
          },
        },
      },
    },
  },
  buildSchema(errs)::
    local codes = std.set(std.map((function(x) x.status), errs));
    local getErrors(c) = std.map($.buildObj, std.filter((function(x) x.status == c), errs));
    {
      [std.toString(code)]: {
        description: responseCodeDescriptions[std.toString(code)],
        content: {
          'application/vnd.api+json': {
            schema: {
              type: 'object',
              properties: {
                errors: {
                  type: 'array',
                  items:
                    local builtErrors = getErrors(code);
                    if std.length(builtErrors) > 1 then
                      { oneOf: builtErrors }
                    else
                      builtErrors[0],
                },
              },
              required: ['errors'],
            },
          },
        },
      }
      for code in codes
    },
  default:: self.buildSchema($.all),
  write:: self.buildSchema($.all + obj.errors),
};

local buildLinks(obj) = {
  read:: {
    type: 'object',
    description: 'Links related to this resource object.',
    properties: {
      'self': {
        type: 'string',
        format: 'uri',
        description: 'The link to the resource representing the resource object.',
        example: std.extVar('baseServer') + '/' + obj.typePlural + '/1',
      },
    },
    required: ['self'],
  },
  readList:: {
    type: 'object',
    description: 'Links related to navigating paginated results.',
    properties: {
      first: {
        type: 'string',
        format: 'uri',
        description: 'The link to the first page.',
        example: std.extVar('baseServer') + '/' + obj.typePlural + '?page[number]=1',
      },
      last: {
        type: 'string',
        format: 'uri',
        description: 'The link to the last page.',
        example: std.extVar('baseServer') + '/' + obj.typePlural + '?page[number]=5',
      },
      prev: {
        type: 'string',
        format: 'uri',
        nullable: true,
        description: 'The link to the previous page. The value will be `null` if requesting the first page.',
        example: std.extVar('baseServer') + '/' + obj.typePlural + '?page[number]=2',
      },
      next: {
        type: 'string',
        format: 'uri',
        nullable: true,
        description: 'The link to the next page. The value will be `null` if requesting the last page.',
        example: std.extVar('baseServer') + '/' + obj.typePlural + '?page[number]=4',
      },
    },
    required: ['first', 'last', 'prev', 'next'],
  },
  readRelatedList(relatedObj):: self.readList {
    properties+: {
      first+: {
        example: std.extVar('baseServer') + '/' + obj.typePlural + '/1/relationships/' + relatedObj.object.typePlural + '?page[number]=1',
      },
      last+: {
        example: std.extVar('baseServer') + '/' + obj.typePlural + '/1/relationships/' + relatedObj.object.typePlural + '?page[number]=5',
      },
      prev+: {
        example: std.extVar('baseServer') + '/' + obj.typePlural + '/1/relationships/' + relatedObj.object.typePlural + '?page[number]=2',
      },
      next+: {
        example: std.extVar('baseServer') + '/' + obj.typePlural + '/1/relationships/' + relatedObj.object.typePlural + '?page[number]=4',
      },
    },
  },
  readRelationshipList(relatedObj):: self.readList {
    properties+: {
      first+: {
        example: std.extVar('baseServer') + '/' + obj.typePlural + '/1/' + relatedObj.object.typePlural + '?page[number]=1',
      },
      last+: {
        example: std.extVar('baseServer') + '/' + obj.typePlural + '/1/' + relatedObj.object.typePlural + '?page[number]=5',
      },
      prev+: {
        example: std.extVar('baseServer') + '/' + obj.typePlural + '/1/' + relatedObj.object.typePlural + '?page[number]=2',
      },
      next+: {
        example: std.extVar('baseServer') + '/' + obj.typePlural + '/1/' + relatedObj.object.typePlural + '?page[number]=4',
      },
    },
  },
  readRelated(relatedObj)::
    local relatedObjType =
      if relatedObj.many then
        relatedObj.object.typePlural
      else
        relatedObj.object.type;
    {
      type: 'object',
      description: 'Links related to this related resource object.',
      properties: {
        'self': {
          type: 'string',
          format: 'uri',
          description: 'The link to the resource that represents the relationship itself.',
          example: std.extVar('baseServer') + '/' + obj.typePlural + '/1/' + relatedObjType,
        },
        related: {
          type: 'string',
          format: 'uri',
          description:
            if relatedObj.many then
              'The link to the resource representing the related resource objects.'
            else
              'The link to the resource representing the related resource object.',
          example: std.extVar('baseServer') + '/' + obj.typePlural + '/1/relationships/' + relatedObjType,
        },
      },
      required: ['self', 'related'],
    },
};

local getAttributes = {
  utils::
    {
      groupAttributes(obj, keys)::
        local keySet = std.set(keys);
        local groupNames = std.set(
          std.map(
            (function(k) obj.attributes[k].oneOfGroup),
            keySet
          )
        );
        if std.length(groupNames) == 1 then
          [keySet]
        else
          local commonKeys = std.filter(
            (function(k) obj.attributes[k].oneOfGroup == ''),
            keySet
          );
          local groupKeys = std.setDiff(keySet, commonKeys);
          local possibleGroupCombinations = utils.cartesianProduct([
            [
              k
              for k in groupKeys
              if obj.attributes[k].oneOfGroup == groupName
            ]
            for groupName in groupNames
            if groupName != ''
          ]);
          std.map(
            (function(x) std.set(x + commonKeys)),
            possibleGroupCombinations
          ),
      getRequiredAttributes(obj, keys)::
        std.filter(
          (function(k) obj.attributes[k].required),
          keys
        ),
      buildObject(obj, keys, required=false)::
        {
          type: 'object',
          title: std.join('/', [k for k in keys if obj.attributes[k].oneOfGroup != '']),
          properties: {
            [k]: obj.attributes[k]
            for k in keys
          },
          [if required then 'required']: $.utils.getRequiredAttributes(obj, keys),
        },
      buildArray(obj, keys, required=false)::
        local groupedKeys = $.utils.groupAttributes(obj, keys);
        std.map(
          (function(x) $.utils.buildObject(obj, x, required)),
          groupedKeys
        ),
    },
  read(obj)::
    local keys = std.filter(
      (function(k) !obj.attributes[k].writeOnly),
      std.objectFields(obj.attributes)
    );
    $.utils.buildArray(obj, keys, required=false),
  write(obj, required=true)::
    local keys = std.filter(
      (function(k) !obj.attributes[k].readOnly),
      std.objectFields(obj.attributes)
    );
    $.utils.buildArray(obj, keys, required=required),
};

local buildResourceIdentifier(obj, required=false) = {
  type: 'object',
  properties: {
    type: {
      type: 'string',
      enum: [obj.type],
      example: self.enum[0],
      description: 'The [type](https://jsonapi.org/format/#document-resource-object-identification) of the resource object.',
    },
    id: {
      type: 'string',
      example: '1',
      pattern: '\\d+',
      description: "The resource object's unique [identify](https://jsonapi.org/format/#document-resource-object-identification). It must locate a single, unique resource.",
    },
  },
  [if required then 'required']: ['type', 'id'],
};

local buildDefaultRelationships(obj) = {
  [relatedObj.object.type]: {
    data: {
      type: relatedObj.object.type,
      id: relatedObj.default,
    },
  }
  for relatedObj in obj.defaultRelationships
};

local buildRelationships(obj, includeLinks=false, required=false, includeDefaults=false, excludeReadOnly=false) = {
  type: 'object',
  description: 'Related resources.',
  [if includeDefaults && std.length(obj.defaultRelationships) > 0 then 'default']: buildDefaultRelationships(obj),
  properties: {
    [if relatedObj.many then relatedObj.object.typePlural else relatedObj.object.type]: {
      local resourceIdentifier = buildResourceIdentifier(
        relatedObj.object,
        required=true
      ) {
        description: 'The related resource data.',
      },
      type: 'object',
      properties: {
        data:
          if relatedObj.many then
            {
              type: 'array',
              items: resourceIdentifier,
              description: 'A list of the related resources.',
            }
          else
            resourceIdentifier,
        [if includeLinks then 'links']: buildLinks(obj).readRelated(relatedObj),
      },
      required:
        if includeLinks then
          ['data', 'links']
        else
          ['data'],
    }
    for relatedObj in std.filter((function(obj) (excludeReadOnly && obj.readOnly) == false), obj.relationships)
  },
  [if required then 'required']: [relatedObj.object.type for relatedObj in obj.relationships if relatedObj.required],
};

local getResource = {
  buildAttributes(attributes)::
    if std.length(attributes) == 1 then
      attributes[0]
    else
      { oneOf: attributes },
  read(obj)::
    local attributes = getAttributes.read(obj);
    buildResourceIdentifier(obj) {
      description: 'The requested resource.',
      properties+: {
        attributes: $.buildAttributes(attributes),
        links: buildLinks(obj).read,
        [if obj.hasRelationships then 'relationships']: buildRelationships(obj, includeLinks=true),
      },
      required: ['type', 'id', 'attributes', 'links'],
    },
  included(obj)::
    local relatedResources = [
      $.read(relatedObj.object) {
        description: 'Included related resources.',
        title: obj.type,
        [if relatedObj.object.hasRelationships then 'relationships']: buildRelationships(relatedObj.object, includeLinks=false),
      }
      for relatedObj in obj.relationships
    ];
    if std.length(relatedResources) == 1 then
      relatedResources[0]
    else
      relatedResources,
  post(obj)::
    local attributes = getAttributes.write(obj, required=true);
    buildResourceIdentifier(obj) {
      properties+: {
        id:: null,
        attributes: $.buildAttributes(attributes),
        [if obj.hasRelationships then 'relationships']: buildRelationships(obj, includeLinks=false, required=true, includeDefaults=true, excludeReadOnly=true),
      },
      required:
        if obj.hasRelationships && !obj.allRelationshipsDefault then
          ['type', 'attributes', 'relationships']
        else
          ['type', 'attributes'],
    },
  patch(obj)::
    local attributes = getAttributes.write(obj, required=false);
    buildResourceIdentifier(obj) {
      properties+: {
        attributes: $.buildAttributes(attributes),
        [if obj.hasRelationships then 'relationships']: buildRelationships(obj, includeLinks=false, required=true),
      },
      required: ['type', 'id'],
    },
  readRelated(obj):: buildResourceIdentifier(obj, required=true),
  writeRelated(obj, nullable=false)::
    buildResourceIdentifier(obj, required=true) {
      [if nullable then 'nullable']: true,
    },
};

local buildSchema(obj) = {
  read:: {
    type: 'object',
    properties: {
      data: getResource.read(obj),
      [if obj.hasRelationships then 'included']: {
        type: 'array',
        items: getResource.included(obj),
      },
      meta: meta.read,
    },
    required: ['data', 'meta'],
  },
  readList:: {
    type: 'object',
    properties: {
      links: buildLinks(obj).readList,
      data: {
        type: 'array',
        items: getResource.read(obj),
      },
      [if obj.hasRelationships then 'included']: {
        type: 'array',
        items: getResource.included(obj),
      },
      meta: meta.readList,
    },
    required: ['links', 'data', 'meta'],
  },
  post:: {
    type: 'object',
    properties: {
      data: getResource.post(obj),
    },
    required: ['data'],
  },
  patch:: {
    type: 'object',
    properties: {
      data: getResource.patch(obj),
    },
    required: ['data'],
  },
  readRelationshipToOne(relatedObj):: buildSchema(relatedObj.object).read,
  readRelatedToOne(relatedObj):: {
    type: 'object',
    properties: {
      data: getResource.readRelated(relatedObj.object) {
        description: 'The resource identifier object of the related resource.',
      },
    },
    required: ['data', 'meta'],
  },
  patchRelatedToOne(relatedObj):: {
    type: 'object',
    properties: {
      data: getResource.writeRelated(relatedObj.object, nullable=true) {
        description: 'The resource identifier object to set as the relationship. Setting to `null` will remove the relationship.',
      },
    },
    required: ['data'],
  },
  readRelationshipToMany(relatedObj):: buildSchema(relatedObj.object).readList {
    properties+: {
      links: buildLinks(obj).readRelationshipList(relatedObj),
    },
    required: ['links', 'data', 'meta'],
  },
  readRelatedToMany(relatedObj):: {
    type: 'object',
    properties: {
      links: buildLinks(obj).readRelatedList(relatedObj),
      data: {
        type: 'array',
        items: getResource.readRelated(relatedObj.object),
        description: 'The resource identifier objects of the related resource.',
      },
    },
    required: ['links', 'data', 'meta'],
  },
  patchRelatedToMany(relatedObj):: {
    type: 'object',
    properties: {
      data: {
        type: 'array',
        items: getResource.writeRelated(relatedObj.object, nullable=false),
        description: 'A list of resource identifier objects to set as the relationship. Setting to an empty array will remove the relationship.',
      },
    },
    required: ['data'],
  },
  postRelatedToMany(relatedObj):: {
    type: 'object',
    properties: {
      data: {
        type: 'array',
        items: getResource.writeRelated(relatedObj.object, nullable=false),
        description: 'A list of resource identifier objects to add to the relationship.',
        minLength: 1,
      },
    },
    required: ['data'],
  },
  deleteRelatedToMany(relatedObj):: {
    type: 'object',
    properties: {
      data: {
        type: 'array',
        items: getResource.writeRelated(relatedObj.object, nullable=false),
        description: 'A list of resource identifier objects to remove from the relationship.',
        minLength: 1,
      },
    },
    required: ['data'],
  },
};

local buildPaths(obj) =
  local builtParameters = buildParameters(obj);
  local builtSchema = buildSchema(obj);
  local builtErrors = buildErrors(obj);
  {
    ['/' + obj.typePlural + '/{id}']: {
      [if std.setInter(["fetch"], obj.allowed_methods_set) != [] then "get"]: {
        tags: [obj.type],
        summary: 'Fetch resource',
        parameters: builtParameters.read,
        responses: builtErrors.default {
          '200': {
            description: 'OK',
            content: {
              'application/vnd.api+json': {
                schema: builtSchema.read,
              },
            },
          },
        },
      },
      [if std.setInter(["update"], obj.allowed_methods_set) != [] then "patch"]: {
        tags: [obj.type],
        summary: 'Update resource',
        parameters: builtParameters.write,
        responses: builtErrors.write {
          '200': {
            description: 'OK',
            content: {
              'application/vnd.api+json': {
                schema: builtSchema.read,
              },
            },
          },
        },
        requestBody: {
          content: {
            'application/vnd.api+json': {
              schema: builtSchema.patch,
            },
          },
        },
      },
      [if std.setInter(["delete"], obj.allowed_methods_set) != [] then "delete"]: {
        tags: [obj.type],
        summary: 'Delete resource',
        parameters: builtParameters.write,
        responses: builtErrors.default {
          '204': {
            description: 'No Content',
          },
        },
      },
    },
    ['/' + obj.typePlural]: {
      [if std.setInter(["list"], obj.allowed_methods_set) != [] then "get"]: {
        tags: [obj.type],
        summary: 'List resources',
        parameters: builtParameters.readList,
        responses: builtErrors.default {
          '200': {
            description: 'OK',
            content: {
              'application/vnd.api+json': {
                schema: builtSchema.readList,
              },
            },
          },
        },
      },
      [if std.setInter(["create"], obj.allowed_methods_set) != [] then "post"]: {
        tags: [obj.type],
        summary: 'Add resource',
        responses: builtErrors.write {
          '201': {
            description: 'Created',
            content: {
              'application/vnd.api+json': {
                schema: builtSchema.read,
              },
            },
          },
        },
        requestBody: {
          content: {
            'application/vnd.api+json': {
              schema: builtSchema.post,
            },
          },
        },
      },
    },
  ['/' + obj.typePlural + '/bulk']: {
    [if std.setInter(['bulk'], obj.allowed_methods_set) != [] then "post"]: {
      tags: [obj.type],
      summary: 'Upload CSV',
      security: [
        {
          tokenAuth: [],
        }
      ],
      responses: builtErrors.write {
        '202': {
          description: 'Accepted',
          content: {
            'application/vnd.api+json': {
              schema: {
                type: 'object',
                properties: {
                  data: {
                    type: 'object',
                    properties: {
                      message: {
                        type: 'string',
                        description: 'A brief success message'
                      }
                    },
                  },
                },
              },
            },
          },
        },
      },
      requestBody: {
        content: {
          'multipart/form-data': {
            schema: {
              type: 'object',
              properties: {
                csv: {
                  type: 'file',
                  description: 'CSV containing the required headers: ' + std.extVar('product_csv_headers')
                },
                images: {
                  type: 'array',
                  items: {
                    type: 'file',
                  },
                  description: '(Optional) Images matching the image_name in the csv',
                },
              },
              required: ['csv'],
            },
          },
        },
      },
    },
  },
  } + {
    ['/' + obj.typePlural + '/{id}/relationships/' + relatedObj.object.typePlural]: {
      get: {
        tags: [obj.type],
        summary: ['Fetch identifiers for related ' + relatedObj.object.type  + ' resources'],
        parameters: builtParameters.write,
        responses: builtErrors.default {
          '200': {
            description: 'OK',
            content: {
              'application/vnd.api+json': {
                schema: builtSchema.readRelatedToMany(relatedObj),
              },
            },
          },
        },
      },
      post:: {
        tags: [obj.type],
        summary: 'Add new related resource',
        parameters: builtParameters.write,
        responses: builtErrors.default {
          '204': {
            description: 'No Content',
          },
        },
        requestBody: {
          content: {
            'application/vnd.api+json': {
              schema: builtSchema.postRelatedToMany(relatedObj),
            },
          },
        },
      },
      patch:: {
        tags: [obj.type],
        summary: 'Update related resources',
        parameters: builtParameters.write,
        responses: builtErrors.default {
          '204': {
            description: 'No Content',
          },
        },
        requestBody: {
          content: {
            'application/vnd.api+json': {
              schema: builtSchema.patchRelatedToMany(relatedObj),
            },
          },
        },
      },
      delete:: {
        tags: [obj.type],
        summary: 'Delete related resources',
        parameters: builtParameters.write,
        responses: builtErrors.default {
          '204': {
            description: 'No Content',
          },
        },
        requestBody: {
          content: {
            'application/vnd.api+json': {
              schema: builtSchema.deleteRelatedToMany(relatedObj),
            },
          },
        },
      },
    }
    for relatedObj in std.filter((function(x) x.many), obj.relationships)
  } + {
    ['/' + obj.typePlural + '/{id}/' + relatedObj.object.typePlural]: {
      get: {
        tags: [obj.type],
        summary: ['Fetch related ' + relatedObj.object.type + ' resources'],
        parameters: builtParameters.write,
        responses: builtErrors.default {
          '200': {
            description: 'OK',
            content: {
              'application/vnd.api+json': {
                schema: builtSchema.readRelationshipToMany(relatedObj),
              },
            },
          },
        },
      },
    }
    for relatedObj in std.filter((function(x) x.many), obj.relationships)
  } + {
    ['/' + obj.typePlural + '/{id}/relationships/' + relatedObj.object.type]: {
      get: {
        tags: [obj.type],
        summary: ['Fetch identifier for related ' + relatedObj.object.type + ' resource'],
        parameters: builtParameters.write,
        responses: builtErrors.default {
          '200': {
            description: 'OK',
            content: {
              'application/vnd.api+json': {
                schema: builtSchema.readRelatedToOne(relatedObj),
              },
            },
          },
        },
      },
      patch:: {
        tags: [obj.type],
        summary: 'Update related resource',
        parameters: builtParameters.write,
        responses: builtErrors.default {
          '204': {
            description: 'No Content',
          },
        },
        requestBody: {
          content: {
            'application/vnd.api+json': {
              schema: builtSchema.patchRelatedToOne(relatedObj),
            },
          },
        },
      },
    }
    for relatedObj in std.filter((function(x) x.many == false), obj.relationships)
  } + {
    ['/' + obj.typePlural + '/{id}/' + relatedObj.object.type]: {
      get: {
        tags: [obj.type],
        summary: ['Fetch related ' + relatedObj.object.type + ' resource'],
        parameters: builtParameters.write,
        responses: builtErrors.default {
          '200': {
            description: 'OK',
            content: {
              'application/vnd.api+json': {
                schema: builtSchema.readRelationshipToOne(relatedObj),
              },
            },
          },
        },
      },
    }
    for relatedObj in std.filter((function(x) x.many == false), obj.relationships)
  };

local buildSpec(objs, description) = {
  local patchedObjs = std.map((function(x) ModelTemplate + x + ModelProcessor), objs),

  openapi: '3.0.3',
  servers: [
    # Todo: Removed hardcoded servers (taken from chemreg app). Replace with valid server addresses if needed.
    #{
    #  url: std.extVar('baseServer'),
    #  description: 'Current server',
    #},
    #{
    #  url: 'https://api.chemreg.epa.gov',
    #  description: 'Production server',
    #},
    #{
    #  url: 'https://ccte-api-chemreg-stg.epa.gov',
    #  description: 'Staging server',
    #},
  ],
  info: {
    description: description,
    title: 'Factotum API',
    version: std.extVar('version'),
    'x-logo': {
      # todo: Add favicon
      # url: std.extVar('baseServer') + '/static/openapi/logo.svg',
      altText: 'Factotum API',
    },
  },
  components: {
    securitySchemes: {
      tokenAuth: {
        type: 'http',
        scheme: 'bearer',
        description: '[Token Authentication](https://www.django-rest-framework.org/api-guide/authentication/#tokenauthentication).',
      },
    },
  },
  security: [],
  tags: [
    {
      name: obj.type,
      description: obj.description,
    }
    for obj in patchedObjs
  ],
  'x-tagGroups': [
    {
      name: app,
      tags: std.set(std.map((function(x) x.type), std.filter((function(x) x.app == app), patchedObjs))),
    }
    for app in std.set(std.map((function(x) x.app), patchedObjs))
  ] + [
    {
      name: "Authentication",
      tags: ['tokenAuth']
    }
  ],
  paths: std.foldl((function(x, y) x + y), std.map(buildPaths, patchedObjs), {}) + import 'auth.libsonnet'
};

{
  buildSpec(objs, description):: buildSpec(objs, description),
}
