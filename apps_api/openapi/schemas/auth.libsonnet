{
  ["/token/"]: {
    post: {
      summary: 'Obtain Token',
      requestBody: {
        content: {
          'application/vnd.api+json': {
            schema: {
              type: "object",
              properties: {
                data: {
                  type: "object",
                  properties: {
                    type: {
                      type: "string",
                      example: "token",
                      description: "The resource name of the token being created",
                    },
                    attributes: {
                      type: "object",
                      properties: {
                        username: {
                          type: "string",
                          description: "Username of a factotum user",
                        },
                        password: {
                          type: "string",
                          description: "Password of a factotum user",
                        },
                      },
                    },
                  },
                },
              },
            },
          },
        },
      },
      responses: {
        '200': {
          description: "OK",
          content: {
            'application/vnd.api+json':{
              schema: {
                type: 'object',
                properties: {
                  token: {
                    type: 'string',
                  },
                },
              },
            },
          },
        }
      },
      "tags": [ "tokenAuth" ],
    },
  },
}