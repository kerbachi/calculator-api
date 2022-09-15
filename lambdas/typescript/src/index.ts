// ts-node src/index.ts 
// npm install
// move node_modules to dist/
// tsc -> Compile JS code in dist/


import Ajv from "ajv"


const schema = {
    type: "object",
    properties: {
      param1: {type: "integer"},
      param2: {type: "string"}
    },
    required: ["param2"],
    additionalProperties: true,
}

const ajv = new Ajv()
const validate = ajv.compile(schema)


export const handler = async (event: any = {}): Promise<any> => {
    console.log('Running Lambda!');
    var response ={}

    console.info("EVENT\n" + JSON.stringify(event, null, 2))
    const special_response=event.queryStringParameters

    if(!validate(special_response)) {
        response = {
            "statusCode": 400,
            "body": JSON.stringify(validate.errors)
        };
    }else {
        response = {
            "statusCode": 200,
            "body": JSON.stringify(special_response)
        };
    }

    return response;
}