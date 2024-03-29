from aws_cdk import(
    Stack,
    RemovalPolicy,
    CfnOutput,
    Aws,
    Duration,
    aws_apigatewayv2_alpha,
    aws_apigatewayv2 as aws_apigatewayv2_stable,
    aws_route53,
    aws_route53_targets,
    aws_lambda,
    aws_certificatemanager as certificatemanager,
    aws_iam as iam,
    aws_cognito as cognito
)
from constructs import Construct
import os


class CalculatorApiStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Variables
        dns_domain = os.environ.get('DNS_DOMAIN', "my-domain.com")
        sub_domain_public = "calculator-api"
        userpool_domain = sub_domain_public
        hosted_zone = aws_route53.HostedZone.from_lookup( self, dns_domain, domain_name=dns_domain )

        ###############################
        # Cognito
        ###############################

        # Cognito Userpool will be deleted when deleting the Stack
        userpool = cognito.UserPool(
            self,
            "UserPool-" +self.stack_name,
            user_pool_name="UserPool-" + self.stack_name,
            removal_policy=RemovalPolicy.DESTROY
        )

        # Add Cognito Username Pool to Cloudformation output
        CfnOutput(
            self,
            "UserPoolID",
            value=userpool.user_pool_id
        )

        userpool.add_domain(
            userpool_domain,
            cognito_domain=cognito.CognitoDomainOptions(
                domain_prefix=userpool_domain
            )
        )

        read_scope = cognito.ResourceServerScope(scope_name="json.read", scope_description="Read-only access")
        write_scope = cognito.ResourceServerScope(scope_name="json.write", scope_description="Full access")

        userpool_resource_servers = cognito.UserPoolResourceServer(
            self,
            "UserPoolResourceServer",
            user_pool=userpool,
            identifier="UserPoolResourceServer",
            scopes=[read_scope, write_scope]
        )

        # For security purpose we don't reveal that the user doesn't exist
        userpool_client = userpool.add_client(
            "client1",
            user_pool_client_name="Client1",
            generate_secret=True,
            auth_flows=cognito.AuthFlow(
                user_srp=True,
                custom=True
            ),
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(
                    client_credentials=True
                ),
                scopes=[cognito.OAuthScope.resource_server(userpool_resource_servers, read_scope)]
            ),
            prevent_user_existence_errors=True,
        )

        # Add Cognito Client ID to Cloudformation output
        CfnOutput(
            self,
            "UserPoolClientID",
            value=userpool_client.user_pool_client_id
        )

        # Add Cognito Client Secret to Cloudformation output
        CfnOutput(
            self,
            "UserPoolClientSecret",
            value=userpool_client.user_pool_client_secret.to_string()
        )

        self.userpool_id = userpool.user_pool_id
        self.userpool_audience = userpool_client.user_pool_client_id
        self.userpool_demain_name = "https://" + userpool_domain + ".auth." + Aws.REGION + ".amazoncognito.com"
        self.jwt_issuer = "https://cognito-idp." + Aws.REGION + ".amazonaws.com/" + self.userpool_id

        ###############################
        # HTTP API
        ###############################
        
        apigw = aws_apigatewayv2_alpha.HttpApi(
            self,
            "calculator_api",
            api_name="calculator_api",
            description="HTTP API to do basic +/- calculation",
            create_default_stage=False
        )

        default_stage = aws_apigatewayv2_alpha.HttpStage(
            self,
            "DefaultStage",
            http_api=apigw,
            stage_name="$default",
            auto_deploy=True
        )

        # Lambda "lambda_plus" in Python
        with open("lambdas/lambda_plus.py", encoding="utf8") as fp:
            handler_code = fp.read()

        lambda_plus = aws_lambda.Function(
            self,
            "lambda_plus",
            function_name="lambda_plus",
            description="Simple lambda to do addition",
            code=aws_lambda.InlineCode(handler_code),
            handler="index.handler",
            timeout=Duration.seconds(3),
            runtime=aws_lambda.Runtime.PYTHON_3_9
        )

        # Permission for HTTP API to call the LAmbda function 
        lambda_plus.add_permission(
            "ApiGwPermLambdaPlus",
            action="lambda:InvokeFunction",
            principal=iam.ServicePrincipal(service="apigateway.amazonaws.com"),
            source_arn="arn:aws:execute-api:" + Aws.REGION + ":" + Aws.ACCOUNT_ID + ":" + apigw.http_api_id +"/*/*/plus"
        )

        # Lambda "lambda_minus" in Typescript
        with open("lambdas/lambda_minus.js", encoding="utf8") as fp:
            handler_code = fp.read()

        lambda_minus = aws_lambda.Function(
            self,
            "lambda_minus",
            function_name="lambda_minus",
            description="Simple lambda to do minus operation",
            code=aws_lambda.InlineCode(handler_code),
            handler="index.handler",
            timeout=Duration.seconds(3),
            runtime=aws_lambda.Runtime.NODEJS_14_X
        )

        # Permission for HTTP API to call the Lambda function   
        lambda_minus.add_permission(
            "ApiGwPermLambdaMinus",
            action="lambda:InvokeFunction",
            principal=iam.ServicePrincipal(service="apigateway.amazonaws.com"),
            source_arn="arn:aws:execute-api:" + Aws.REGION + ":" + Aws.ACCOUNT_ID + ":" + apigw.http_api_id +"/*/*/minus"
        )
        
        # Lambda "lambda_default_route" in Python
        with open("lambdas/lambda_default_route.py", encoding="utf8") as fp:
            handler_code = fp.read()

        lambda_default_route = aws_lambda.Function(
            self,
            "lambda_default_route",
            function_name="lambda_default_route",
            description="lambda for default route",
            code=aws_lambda.InlineCode(handler_code),
            handler="index.handler",
            timeout=Duration.seconds(3),
            runtime=aws_lambda.Runtime.PYTHON_3_9
        )

        # Permission for HTTP API to call the Lambda function   
        lambda_default_route.add_permission(
            "ApiGwPermLambdaDefaultRoute",
            action="lambda:InvokeFunction",
            principal=iam.ServicePrincipal(service="apigateway.amazonaws.com"),
            source_arn="arn:aws:execute-api:" + Aws.REGION + ":" + Aws.ACCOUNT_ID + ":" + apigw.http_api_id +"/*/$default"
        )
   
        # Default Integration + default authorizer (JWT)
        default_integration = aws_apigatewayv2_alpha.HttpIntegration(
            self,
            "DefaultIntegration",
            http_api=apigw,
            integration_type=aws_apigatewayv2_alpha.HttpIntegrationType.AWS_PROXY, # LAMBDA_PROXY for cdk v1
            integration_uri=lambda_default_route.function_arn,
            method=aws_apigatewayv2_alpha.HttpMethod.ANY,
            payload_format_version=aws_apigatewayv2_alpha.PayloadFormatVersion.VERSION_2_0,
            secure_server_name=sub_domain_public + '.' + dns_domain
        )

        jwt_authorizer = aws_apigatewayv2_alpha.HttpAuthorizer(
            self,
            "JWTAuthorizer",
            http_api=apigw,
            identity_source=["$request.header.Authorization"],
            type=aws_apigatewayv2_alpha.HttpAuthorizerType.JWT,
            authorizer_name="JWTAuthorizer",
            jwt_audience=[self.userpool_audience],
            jwt_issuer=self.jwt_issuer
        )

        # Default route without authentication
        http_api_route_default = aws_apigatewayv2_stable.CfnRoute(
            self,
            "RouteDefault",
            api_id=apigw.api_id,
            route_key="$default",
            authorization_type="NONE",
            # authorizer_id=jwt_authorizer.authorizer_id,
            target="integrations/"+default_integration.integration_id
        )

        http_api_route_default.node.add_dependency(default_integration)

        # Route /plus with lambda_plus
        endpoint_plus_integration = aws_apigatewayv2_alpha.HttpIntegration(
            self,
            "IntegrationPlus",
            http_api=apigw,
            integration_type=aws_apigatewayv2_alpha.HttpIntegrationType.AWS_PROXY, # LAMBDA_PROXY for cdk v1
            integration_uri=lambda_plus.function_arn,
            method=aws_apigatewayv2_alpha.HttpMethod.ANY,
            payload_format_version=aws_apigatewayv2_alpha.PayloadFormatVersion.VERSION_2_0,
            secure_server_name=sub_domain_public + '.' + dns_domain
        )

        http_api_route_lambda_plus = aws_apigatewayv2_stable.CfnRoute(
            self,
            "Route_lambda_plus",
            api_id=apigw.api_id,
            route_key="GET /plus",
            authorization_type="JWT",
            authorizer_id=jwt_authorizer.authorizer_id,
            target="integrations/" + endpoint_plus_integration.integration_id
        )


        # Route /minus with lambda_minus
        endpoint_minus_integration = aws_apigatewayv2_alpha.HttpIntegration(
            self,
            "IntegrationMinus",
            http_api=apigw,
            integration_type=aws_apigatewayv2_alpha.HttpIntegrationType.AWS_PROXY, # LAMBDA_PROXY for cdk v1
            integration_uri=lambda_minus.function_arn,
            method=aws_apigatewayv2_alpha.HttpMethod.GET,
            payload_format_version=aws_apigatewayv2_alpha.PayloadFormatVersion.VERSION_2_0,
            secure_server_name=sub_domain_public + '.' + dns_domain
        )

        http_api_route_lambda_minus = aws_apigatewayv2_stable.CfnRoute(
            self,
            "Route_lambda_minus",
            api_id=apigw.api_id,
            route_key="GET /minus",
            authorization_type="JWT",
            authorizer_id=jwt_authorizer.authorizer_id,
            target="integrations/" + endpoint_minus_integration.integration_id
        )

        http_api_route_default.node.add_dependency(default_integration)

        # Oauth2 Authentication Route
        oauth2_integration = aws_apigatewayv2_alpha.HttpIntegration(
            self,
            "Oauth2Integration",
            http_api=apigw,
            integration_type=aws_apigatewayv2_alpha.HttpIntegrationType.HTTP_PROXY,
            connection_type=aws_apigatewayv2_alpha.HttpConnectionType.INTERNET,
            method=aws_apigatewayv2_alpha.HttpMethod.ANY,
            payload_format_version=aws_apigatewayv2_alpha.PayloadFormatVersion.VERSION_1_0,
            integration_uri=self.userpool_demain_name + "/oauth2/token"
        )

        http_api_oauth2_route = aws_apigatewayv2_stable.CfnRoute(
            self,
            "Oauth2Default",
            api_id=apigw.api_id,
            route_key="ANY /oauth2/token",
            target="integrations/" +  oauth2_integration.integration_id
        )

        ###############################
        # SSL Certificate
        ###############################

        # Public ACM Certificate
        acm_certificate_public = certificatemanager.Certificate(
                self,
                id="ACMPublicSubdomain" + self.stack_name,
                domain_name=(sub_domain_public + '.' + dns_domain).lower(),
                validation=certificatemanager.CertificateValidation.from_dns(hosted_zone=hosted_zone)
        )

        ###############################
        # Custom Domain & ApiMapping
        ###############################

        custom_domain = aws_apigatewayv2_alpha.DomainName(
            self,
            "CustomDomain",
            certificate=acm_certificate_public,
            domain_name=sub_domain_public + "." + dns_domain
        )

        custom_domain.node.add_dependency(apigw)

        api_mapping = aws_apigatewayv2_alpha.ApiMapping(
            self,
            "ApiMapping",
            api=apigw,
            domain_name=custom_domain,
            stage=default_stage
        )

        # api_mapping.node.add_dependency(custom_domain)
        # api_mapping.node.add_dependency(default_stage)

        custom_domain_name = aws_route53.RecordSet(
            self,
            "RecordSet" + self.stack_name,
            record_type=aws_route53.RecordType.A,
            target=aws_route53.RecordTarget.from_alias(aws_route53_targets.ApiGatewayv2DomainProperties(
                regional_domain_name=custom_domain.regional_domain_name,
                regional_hosted_zone_id=custom_domain.regional_hosted_zone_id
            )),
            zone=hosted_zone,
            comment="RecordSet for Stack " + self.stack_name,
            record_name=sub_domain_public
        )

        # Add DNS name to Cloudformation output
        CfnOutput(
            self,
            "DnsRecord",
            value=custom_domain_name.domain_name
        )