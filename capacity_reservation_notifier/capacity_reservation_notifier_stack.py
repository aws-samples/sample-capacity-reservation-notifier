from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as lambda_,
    aws_sns as sns,
    aws_iam as iam,
    aws_logs as logs,
    aws_scheduler as scheduler,
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
                "SNS_TOPIC_ARN": topic.topic_arn
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
            schedule_expression="cron(0 0 * * ? *)",
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
            schedule_expression="cron(0 10 * * ? *)",
            flexible_time_window=scheduler.CfnSchedule.FlexibleTimeWindowProperty(
                mode="OFF"
            ),
            target=scheduler.CfnSchedule.TargetProperty(
                arn=lambda_function.function_arn,
                role_arn=scheduler_role.role_arn
            )
        )

        # Outputs
        CfnOutput(self, "SNSTopicArn", value=topic.topic_arn)
        CfnOutput(self, "LambdaFunctionArn", value=lambda_function.function_arn)
        CfnOutput(self, "LambdaFunctionName", value=lambda_function.function_name)
