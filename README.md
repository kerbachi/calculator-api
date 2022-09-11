
# Welcome to the Calculator API projet!

This is a demo project to deploy a calculator API using AWS CDK with Python.

# Environment Setup
The `cdk.json` file tells the CDK Toolkit how to execute your app.

This project is set up like a standard Python project.  The initialization
process also creates a virtualenv within this project, stored under the `.venv`
directory.  To create the virtualenv it assumes that there is a `python3`
(or `python` for Windows) executable in your path with access to the `venv`
package. If for any reason the automatic creation of the virtualenv fails,
you can create the virtualenv manually.

To manually create a virtualenv on MacOS and Linux:

```bash
$ python -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```bash
$ source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```bash
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```bash
$ pip install -r requirements.txt
```

At this point you can now deploy the CloudFormation template for this code.
Assign DNS_DOMAIN a DNS domain from your Route53 account

```bash
$ export CDK_DEFAULT_ACCOUNT=012345678910
$ export CDK_DEFAULT_REGION='us-east-1'
$ export DNS_DOMAIN='YOUR_ROUTE53_DOMAIN'
$ cdk synth
```

This will deploy the API HTTP with the custom domain https://calculator-api.my-domain.com
The authentication will done with the endpoint https://calculator-api.my-domain.com/oauth2/token


# Get OAuth2 token

There are many GUIs you can use to generate the JWT token like Postman or Insomnia. We'll use here the old curl command

Get first the `UserPoolID` and the `UserPoolClientID` created by the CDK 

![Alt text](pictures/cdk%20output.png)


Uset them with `aws cognito-idp` to get the `ClientId` and the `ClientSecret`

```bash
aws cognito-idp describe-user-pool-client --user-pool-id us-east-1_LX6a3ggxu --client-id 618jhi0ako4kukld7rsh8tuq2g
{
    "UserPoolClient": {
        "UserPoolId": "us-east-1_LX6a3ggxu",
        "ClientName": "Client1",
        "ClientId": "618jhi0ako4kukld7rsh8tuq2g",
        "ClientSecret": "e174jlu5mdkr6o1vedp5tvc4rs6lei1nqlapufjc14lup7lhim5",
        "LastModifiedDate": "2021-12-22T14:30:31.698000-05:00",
        "CreationDate": "2021-12-22T14:30:31.698000-05:00",
        "RefreshTokenValidity": 30,
        "TokenValidityUnits": {},
        "ExplicitAuthFlows": [
            "ALLOW_CUSTOM_AUTH",
            "ALLOW_REFRESH_TOKEN_AUTH",
            "ALLOW_USER_SRP_AUTH"
        ],
        "SupportedIdentityProviders": [
            "COGNITO"
        ],
        "AllowedOAuthFlows": [
            "client_credentials"
        ],
        "AllowedOAuthScopes": [
            "UserPoolResourceServer/json.read"
        ],
        "AllowedOAuthFlowsUserPoolClient": true,
        "PreventUserExistenceErrors": "ENABLED"
    }
}
```


We'll convert the ClientId and ClientSecret to generate the JWT token (in Base64)

```python
$python
>>> import base64
>>> base64_encoded=base64.b64encode(b'618jhi0ako4kukld7rsh8tuq2g:e174jlu5mdkr6o1vedp5tvc4rs6lei1nqlapufjc14lup7lhim5')
>>> print(base64_encoded)
b'NjE4amhpMGFrbzRrdWtsZDdyc2g4dHVxMmc6ZTE3NGpsdTVtZGtyNm8xdmVkcDV0dmM0cnM2bGVpMW5xbGFwdWZqYzE0bHVwN2xoaW01'
```

We'll use that JWT token to authenticate with the API HTTP Gateway using the endpoint /oauth2/token

```bash
curl --location --request POST 'https://calculator-api.my-domain.com/oauth2/token?grant_type=client_credentials&client_id=618jhi0ako4kukld7rsh8tuq2g$scope=AuthIdentifier/json.read' \
                    --header 'Authorization: Basic NjE4amhpMGFrbzRrdWtsZDdyc2g4dHVxMmc6ZTE3NGpsdTVtZGtyNm8xdmVkcDV0dmM0cnM2bGVpMW5xbGFwdWZqYzE0bHVwN2xoaW01' \
                    --header 'Content-Type: application/x-x-www-form-urlencoded'

{"access_token":"eyJraWQiOiJRcHNTWU5oVjJFRzNpQ1d6bDd2SVM4N....................................","expires_in":"3600","token_type":"Bearer"}
```

# Query the API endpoints with OAuth2 token

Now we can query the API Gateway using this token

```bash
curl --location --request GET 'https://calculator-api.my-domain.com/minus?val1=3&val2=10' --header 'Content-Type: application/json' --header 'Authorization: Bearer eyJraWQiOiJRcHNTWU5oVjJFRzNpQ1d6bDd2SVM4N...................................." \
        --header 'Content-Type: application/json'
7
```
The result `7` (10-3) is returned from the Lambda `lambda_minus`


However, the default route (in our case the root path) doesn't need  authentication 

```bash
$ curl --request GET https://calculator-api.my-domain.com
Hello! This is the default route.
 received event: {"version": "2.0", "routeKey": "$default", "rawPath": "/", "rawQueryString": "", "headers": {"accept": "*/*", "content-length": "0", "host": "calculator-api.my-domain.com", "user-agent": "curl/7.75.0", "x-amzn-trace-id": "Root=1-61c38f44-6762a5b730fd53e1428fcaab", "x-forwarded-for": "44.33.22.11", "x-forwarded-port": "443", "x-forwarded-proto": "https"}, "requestContext": {"accountId": "012345678910", "apiId": "f9va58ihri", "domainName": "calculator-api.my-domain.com", "domainPrefix": "calculator-api", "http": {"method": "GET", "path": "/", "protocol": "HTTP/1.1", "sourceIp": "44.33.22.11", "userAgent": "curl/7.75.0"}, "requestId": "KxNSxgU2IAMEVvc=", "routeKey": "$default", "stage": "$default", "time": "22/Dec/2021:20:49:08 +0000", "timeEpoch": 1640206148700}, "isBase64Encoded": false}(.venv)
```

# TODO

* Switch to CDK v2





Enjoy!