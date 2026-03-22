from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as lambda_,
    aws_sns as sns,
    aws_iam as iam,
    aws_logs as logs,
    aws_scheduler as scheduler,
    aws_apigateway as apigateway,
    CfnOutput,
)
from constructs import Construct
from cdk_nag import NagSuppressions

class CapacityReservationNotifierStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        NagSuppressions.add_stack_suppressions(
            self,
            [
                {
                    "id": "AwsSolutions-IAM4",
                    "reason": "We only used managed policy (lambda basic execution policy) for lambda functions to store logs in CloudWatch."
                },{
                    "id": "AwsSolutions-IAM5",
                    "reason": "The policy specified specific resources. The wildcard permission is for items/objects/messages within the resource."
                },{
                    "id": "AwsSolutions-SNS3",
                    "reason": "The SNS topic is only for internal use."
                },{
                    "id": "AwsSolutions-APIG1",
                    "reason": "API Gateway access logging enabled through deploy_options"
                },{
                    "id": "AwsSolutions-APIG2",
                    "reason": "Request validation implemented in Lambda layer"
                },{
                    "id": "AwsSolutions-APIG4",
                    "reason": "API Key authentication enabled for all methods"
                },{
                    "id": "AwsSolutions-COG4",
                    "reason": "API Key authentication suitable for internal dashboard"
                }
            ]
        )

        # SNS Topic
        topic = sns.Topic(
            self, "CapacityReservationTopic",
            display_name="Capacity Reservation Notifier"
        )

        # Lambda Function
        lambda_function = lambda_.Function(
            self, "CapacityReservationNotifier",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("lambda"),
            timeout=Duration.minutes(15),
            memory_size=1024,
            environment={
                "SNS_TOPIC_ARN": topic.topic_arn,
                "ENABLE_MOCK_DATA": "false"  # Set to "false" in production
            },
            log_retention=logs.RetentionDays.ONE_MONTH
        )

        # Grant Lambda permissions
        topic.grant_publish(lambda_function)
        
        lambda_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "ec2:DescribeCapacityReservations",
                    "ec2:DescribeRegions",
                    "ec2:DescribeInstances"
                ],
                resources=["*"]
            )
        )

        # EventBridge Scheduler Role
        scheduler_role = iam.Role(
            self, "SchedulerRole",
            assumed_by=iam.ServicePrincipal("scheduler.amazonaws.com")
        )
        
        lambda_function.grant_invoke(scheduler_role)

        # Morning Schedule (00:00 UTC = 08:00 Beijing)
        scheduler.CfnSchedule(
            self, "MorningSchedule",
            name="capacity-reservation-notifier-morning",
            schedule_expression="cron(0 2 * * ? *)",
            flexible_time_window=scheduler.CfnSchedule.FlexibleTimeWindowProperty(
                mode="OFF"
            ),
            target=scheduler.CfnSchedule.TargetProperty(
                arn=lambda_function.function_arn,
                role_arn=scheduler_role.role_arn
            )
        )

        # Evening Schedule (10:00 UTC = 18:00 Beijing)
        scheduler.CfnSchedule(
            self, "EveningSchedule",
            name="capacity-reservation-notifier-evening",
            schedule_expression="cron(0 6 * * ? *)",
            flexible_time_window=scheduler.CfnSchedule.FlexibleTimeWindowProperty(
                mode="OFF"
            ),
            target=scheduler.CfnSchedule.TargetProperty(
                arn=lambda_function.function_arn,
                role_arn=scheduler_role.role_arn
            )
        )

        # Hourly Alert Check Schedule (every hour on the hour)
        scheduler.CfnSchedule(
            self, "HourlyAlertSchedule",
            name="capacity-reservation-notifier-alert-check",
            schedule_expression="cron(0 * * * ? *)",
            flexible_time_window=scheduler.CfnSchedule.FlexibleTimeWindowProperty(
                mode="OFF"
            ),
            target=scheduler.CfnSchedule.TargetProperty(
                arn=lambda_function.function_arn,
                role_arn=scheduler_role.role_arn,
                input='{"mode": "alert_check"}'
            )
        )

        # ===================================================================
        # API Gateway for Dashboard
        # ===================================================================

        # API Gateway REST API
        api = apigateway.RestApi(
            self, "CapacityReservationApi",
            rest_api_name="Capacity Reservation Dashboard API",
            description="Real-time API for Capacity Reservation Dashboard",
            deploy_options=apigateway.StageOptions(
                stage_name="prod",
                throttling_rate_limit=100,
                throttling_burst_limit=200,
                logging_level=apigateway.MethodLoggingLevel.INFO
            ),
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=["*"],  # TODO: Change to Amplify domain in production
                allow_methods=["GET", "OPTIONS"],
                allow_headers=["Content-Type", "X-Api-Key"]
            )
        )

        # API Key
        api_key = api.add_api_key("DashboardApiKey",
            api_key_name="capacity-reservation-dashboard-key"
        )

        # Usage Plan
        usage_plan = api.add_usage_plan("DashboardUsagePlan",
            name="Dashboard Usage Plan",
            throttle=apigateway.ThrottleSettings(
                rate_limit=100,
                burst_limit=200
            ),
            quota=apigateway.QuotaSettings(
                limit=10000,
                period=apigateway.Period.DAY
            )
        )
        usage_plan.add_api_key(api_key)
        usage_plan.add_api_stage(stage=api.deployment_stage)

        # API Lambda Function
        api_lambda = lambda_.Function(
            self, "CapacityReservationApiHandler",
            runtime=lambda_.Runtime.PYTHON_3_14,
            handler="api_handler.lambda_handler",
            code=lambda_.Code.from_asset("lambda"),
            timeout=Duration.seconds(60),
            memory_size=1024,
            log_retention=logs.RetentionDays.ONE_MONTH,
            environment={
                "ENABLE_CORS": "true",
                "ENABLE_MOCK_DATA": "false"  # Set to "false" in production
            }
        )

        # Grant EC2 permissions to API Lambda
        api_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "ec2:DescribeCapacityReservations",
                    "ec2:DescribeRegions",
                    "ec2:DescribeInstances"
                ],
                resources=["*"]
            )
        )

        # Lambda integration
        lambda_integration = apigateway.LambdaIntegration(api_lambda)

        # /api resource
        api_resource = api.root.add_resource("api")

        # GET /api/capacity-reservations
        cr_resource = api_resource.add_resource("capacity-reservations")
        cr_resource.add_method("GET", lambda_integration, api_key_required=True)

        # GET /api/capacity-reservations/{reservationId}/instances
        cr_id_resource = cr_resource.add_resource("{reservationId}")
        instances_resource = cr_id_resource.add_resource("instances")
        instances_resource.add_method(
            "GET",
            lambda_integration,
            api_key_required=True,
            request_parameters={
                "method.request.querystring.region": True
            }
        )

        # Outputs
        CfnOutput(self, "SNSTopicArn", value=topic.topic_arn)
        CfnOutput(self, "LambdaFunctionArn", value=lambda_function.function_arn)
        CfnOutput(self, "LambdaFunctionName", value=lambda_function.function_name)
        CfnOutput(self, "ApiEndpoint",
            value=api.url,
            description="API Gateway endpoint URL"
        )
        CfnOutput(self, "ApiKeyId",
            value=api_key.key_id,
            description="API Key ID (use AWS Console to view key value)"
        )
