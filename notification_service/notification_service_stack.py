from aws_cdk import (
    Duration,
    Stack,
    CfnOutput,
    RemovalPolicy,
    aws_sqs as sqs,
    aws_events as events,
    aws_events_targets as targets,
)
from constructs import Construct


class NotificationServiceStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create SQS Queue for notifications
        notification_queue = sqs.Queue(
            self,
            "NotificationQueue",
            queue_name="notification-service-queue",
            visibility_timeout=Duration.seconds(300),
            retention_period=Duration.days(14),
            removal_policy=RemovalPolicy.DESTROY,  # Change to RETAIN for production
        )

        # Create EventBridge Rule to capture events
        event_rule = events.Rule(
            self,
            "NotificationRule",
            event_pattern=events.EventPattern(
                source=["custom.notifications"],
                detail_type=["notification"],
            ),
            description="Route notification events to SQS queue",
        )

        # Add SQS queue as target for the EventBridge rule
        event_rule.add_target(
            targets.SqsQueue(
                queue=notification_queue,
                message=events.RuleTargetInput.from_object({
                    "timestamp": events.EventField.from_path("$.time"),
                    "source": events.EventField.from_path("$.source"),
                    "detail": events.EventField.from_path("$.detail"),
                }),
            )
        )

        # Output the queue URL and ARN
        CfnOutput(
            self,
            "NotificationQueueUrl",
            value=notification_queue.queue_url,
            description="URL of the SQS notification queue",
        )

        CfnOutput(
            self,
            "NotificationQueueArn",
            value=notification_queue.queue_arn,
            description="ARN of the SQS notification queue",
        )

        CfnOutput(
            self,
            "EventRuleArn",
            value=event_rule.rule_arn,
            description="ARN of the EventBridge rule",
        )
