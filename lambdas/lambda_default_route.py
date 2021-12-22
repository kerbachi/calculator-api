import json

def handler(event, context):
    print("received event: {}".format(event))

    message="Hello! This is the default route without authentication.\nReceived event: " + json.dumps(event)
    response ={
        "statusCode": 200,
        "body": message
    }
    return response