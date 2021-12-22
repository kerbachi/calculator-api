import json

def handler(event, context):
    print(event)
    print(event['queryStringParameters'])

    
    def return_result(status_code, message):
        print(status_code, message)
        response ={
            "statusCode": status_code,
            "body": message
        }
        return response

    try:
        val1 = int(event['queryStringParameters']['val1'])
        val2 = int(event['queryStringParameters']['val2'])
        print(return_result(200, val1 + val2))
        return return_result(200, val1 + val2)
    except ValueError as verr:
        message="The value must be a valide integer"
        print(return_result(400, message))
        return return_result(400, message)
    except Exception as ex:
        message="can not convert to integer"
        print(return_result(400, message))
        return return_result(400, message)