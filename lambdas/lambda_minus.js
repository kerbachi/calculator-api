'use strict';
console.log('Loading substraction function');


exports.handler = async (event) => {
    console.log("request: " + JSON.stringify(event));
    console.log("val1: " + JSON.stringify(event['queryStringParameters']['val1']))
    console.log("val2: " + JSON.stringify(event['queryStringParameters']['val2']))


    let var1 = parseInt(JSON.stringify(event['queryStringParameters']['val1']).slice(1,-1))
    let var2 = parseInt(JSON.stringify(event['queryStringParameters']['val2']).slice(1,-1))
    const diff = var2 - var1
    console.log({"var1": var1, "var2": var2, "diff": diff})

    const responseCode = 200;

    let response = {
        statusCode: responseCode,
        body: diff
    };
    return response;
}