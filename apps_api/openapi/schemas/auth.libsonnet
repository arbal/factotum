{
  ["/token/"]: {
    post: {
      summary: 'Obtain Token',
      requestBody: {
        content: {
          'application/x-www-form-urlencoded': {
            schema: {
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
              }
            },
          },
        },
      },
      responses: {
        '200': {
          description: "A JSON array of user names",
          content: {
            'application/vnd.api+json':{
              schema: {
                type: 'array',
                items: {
                  type: 'string',
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