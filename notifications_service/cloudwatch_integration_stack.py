"""
CloudWatch Integration Stack

Integrates with AWS CloudWatch for:
- Service quota monitoring
- Cost anomaly detection
- Health events
- Custom metric alarms
"""

from aws_cdk import (
    Stack,
    Duration,
    CfnOutput,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    aws_events as events,
    aws_events_targets as targets,
    aws_lambda as lambda_,
    aws_sns as sns,
)
from constructs import Construct


class CloudWatchIntegrationStack(Stack):
    """
    CloudWatch Integration Stack

    Creates CloudWatch alarms that trigger notifications via EventBridge
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        eventbridge_stack,
        lambda_stack,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        environment = self.node.try_get_context("environment") or "dev"

        # SNS Topic for CloudWatch alarms
        alarm_topic = sns.Topic(
            self,
            "AlarmTopic",
            topic_name=f"notifications-{environment}-cloudwatch-alarms",
            display_name="CloudWatch Alarms for Notifications Service"
        )

        # Example 1: Lambda Concurrent Executions Alarm
        lambda_concurrency_alarm = cloudwatch.Alarm(
            self,
            "LambdaConcurrencyAlarm",
            alarm_name=f"ServiceQuota-Lambda-Concurrency-{environment}",
            alarm_description="Alert when Lambda concurrent executions reach 80% of limit",
            metric=cloudwatch.Metric(
                namespace="AWS/Lambda",
                metric_name="ConcurrentExecutions",
                statistic="Maximum",
                period=Duration.minutes(5)
            ),
            threshold=800,  # 80% of 1000 default limit
            evaluation_periods=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )

        # Example 2: DynamoDB Throttled Requests
        dynamodb_throttle_alarm = cloudwatch.Alarm(
            self,
            "DynamoDbThrottleAlarm",
            alarm_name=f"ServiceQuota-DynamoDB-Throttled-{environment}",
            alarm_description="Alert when DynamoDB requests are being throttled",
            metric=cloudwatch.Metric(
                namespace="AWS/DynamoDB",
                metric_name="UserErrors",
                statistic="Sum",
                period=Duration.minutes(5)
            ),
            threshold=10,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD
        )

        # Example 3: API Gateway 5XX Errors
        api_error_alarm = cloudwatch.Alarm(
            self,
            "ApiGateway5XXAlarm",
            alarm_name=f"API-5XX-Errors-{environment}",
            alarm_description="Alert on API Gateway 5XX errors",
            metric=cloudwatch.Metric(
                namespace="AWS/ApiGateway",
                metric_name="5XXError",
                statistic="Sum",
                period=Duration.minutes(5)
            ),
            threshold=5,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD
        )

        # Example 4: Lambda Function Errors
        lambda_error_alarm = cloudwatch.Alarm(
            self,
            "LambdaErrorAlarm",
            alarm_name=f"Lambda-Errors-{environment}",
            alarm_description="Alert on Lambda function errors",
            metric=lambda_stack.slack_notifier.metric_errors(
                period=Duration.minutes(5)
            ),
            threshold=3,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD
        )

        # Add SNS actions to all alarms
        alarms = [
            lambda_concurrency_alarm,
            dynamodb_throttle_alarm,
            api_error_alarm,
            lambda_error_alarm
        ]

        for alarm in alarms:
            alarm.add_alarm_action(cw_actions.SnsAction(alarm_topic))
            alarm.add_ok_action(cw_actions.SnsAction(alarm_topic))

        # EventBridge Rule: CloudWatch Alarm State Changes
        alarm_state_rule = events.Rule(
            self,
            "CloudWatchAlarmStateChange",
            rule_name=f"notifications-{environment}-cw-alarm-state",
            event_bus=eventbridge_stack.event_bus,
            description="Route CloudWatch alarm state changes to notifications",
            event_pattern=events.EventPattern(
                source=["aws.cloudwatch"],
                detail_type=["CloudWatch Alarm State Change"],
                detail={
                    "alarmName": [
                        {"prefix": "ServiceQuota-"},
                        {"prefix": "API-"},
                        {"prefix": "Lambda-"}
                    ]
                }
            )
        )

        # Target: Slack Notifier Lambda
        alarm_state_rule.add_target(
            targets.LambdaFunction(lambda_stack.slack_notifier)
        )

        # EventBridge Rule: AWS Health Events
        health_event_rule = events.Rule(
            self,
            "AWSHealthEvents",
            rule_name=f"notifications-{environment}-health-events",
            event_bus=eventbridge_stack.event_bus,
            description="Route AWS Health events to notifications",
            event_pattern=events.EventPattern(
                source=["aws.health"],
                detail_type=["AWS Health Event"]
            ),
            enabled=True
        )

        health_event_rule.add_target(
            targets.LambdaFunction(lambda_stack.slack_notifier)
        )

        # Lambda function to transform CloudWatch alarm events
        alarm_transformer = lambda_.Function(
            self,
            "AlarmTransformer",
            function_name=f"notifications-{environment}-alarm-transformer",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="index.lambda_handler",
            code=lambda_.Code.from_inline("""
import json

def lambda_handler(event, context):
    '''Transform CloudWatch alarm to notification format'''

    detail = event.get('detail', {})
    alarm_name = detail.get('alarmName', 'Unknown')
    state = detail.get('state', {}).get('value', 'UNKNOWN')
    reason = detail.get('state', {}).get('reason', 'No reason provided')

    # Determine priority based on alarm name
    priority = 'high' if 'ServiceQuota' in alarm_name else 'normal'
    if state == 'ALARM':
        priority = 'critical' if 'ServiceQuota' in alarm_name else 'high'

    # Format for notification service
    notification = {
        'message': f'{alarm_name}: {reason}',
        'priority': priority,
        'alarm_name': alarm_name,
        'state': state,
        'reason': reason,
        'timestamp': detail.get('state', {}).get('timestamp')
    }

    return {
        'statusCode': 200,
        'body': json.dumps(notification)
    }
            """),
            timeout=Duration.seconds(10),
            description="Transforms CloudWatch alarms to notification format"
        )

        # Outputs
        CfnOutput(
            self,
            "AlarmTopicArn",
            value=alarm_topic.topic_arn,
            description="SNS topic ARN for CloudWatch alarms"
        )

        CfnOutput(
            self,
            "LambdaConcurrencyAlarmName",
            value=lambda_concurrency_alarm.alarm_name,
            description="Lambda concurrency alarm name"
        )

        CfnOutput(
            self,
            "AlarmStateRuleName",
            value=alarm_state_rule.rule_name,
            description="EventBridge rule for alarm state changes"
        )

        CfnOutput(
            self,
            "HealthEventRuleName",
            value=health_event_rule.rule_name,
            description="EventBridge rule for AWS Health events"
        )
