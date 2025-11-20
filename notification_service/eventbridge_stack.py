"""
EventBridge Stack for Notifications Service

This stack creates:
- Custom EventBridge event bus
- Multiple EventBridge rules for different event types
- CloudWatch log groups for event logging
- Event archive for replay capability
- Integration with existing SQS queue (optional)
"""

from aws_cdk import (
    Stack,
    aws_events as events,
    aws_events_targets as targets,
    aws_logs as logs,
    aws_sqs as sqs,
    aws_lambda as lambda_,
    CfnOutput,
    RemovalPolicy,
    Duration,
)
from constructs import Construct
from typing import Optional


class EventBridgeStack(Stack):
    """
    EventBridge Stack - Advanced event bus and routing
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        event_processor: Optional[lambda_.IFunction] = None,
        slack_notifier: Optional[lambda_.IFunction] = None,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get environment from context (defaults to 'dev')
        environment = self.node.try_get_context("environment") or "dev"

        # Create custom event bus
        self.event_bus = events.EventBus(
            self,
            "NotificationServiceBus",
            event_bus_name=f"notifications-service-{environment}-bus",
            description=f"Custom event bus for notifications service ({environment})"
        )

        # Create CloudWatch log group for EventBridge events
        self.log_group = logs.LogGroup(
            self,
            "EventBridgeLogGroup",
            log_group_name=f"/aws/events/notifications-service-{environment}",
            retention=logs.RetentionDays.ONE_WEEK if environment == "dev" else logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY if environment == "dev" else RemovalPolicy.RETAIN
        )

        # Create CloudWatch Logs target for all events (useful for debugging)
        log_target = targets.CloudWatchLogGroup(self.log_group)

        # Rule 1: Catch-all rule for logging (helps with debugging)
        catch_all_rule = events.Rule(
            self,
            "CatchAllRule",
            rule_name=f"notifications-{environment}-catch-all",
            event_bus=self.event_bus,
            description="Log all events for debugging",
            event_pattern=events.EventPattern(
                source=events.Match.prefix("")  # Matches all sources
            ),
            enabled=True if environment == "dev" else False  # Only enable in dev
        )
        catch_all_rule.add_target(log_target)

        # Rule 2: Custom application events
        self.custom_events_rule = events.Rule(
            self,
            "CustomEventsRule",
            rule_name=f"notifications-{environment}-custom-events",
            event_bus=self.event_bus,
            description="Route custom application events",
            event_pattern=events.EventPattern(
                source=["custom.notifications"],
                detail_type=events.Match.prefix("")  # All detail types from this source
            )
        )
        # Log custom events
        self.custom_events_rule.add_target(log_target)

        # Add event processor Lambda as target if provided
        if event_processor:
            self.custom_events_rule.add_target(
                targets.LambdaFunction(event_processor)
            )

        # Rule 3: High-priority notifications
        high_priority_rule = events.Rule(
            self,
            "HighPriorityRule",
            rule_name=f"notifications-{environment}-high-priority",
            event_bus=self.event_bus,
            description="Route high-priority/urgent notifications",
            event_pattern=events.EventPattern(
                source=["custom.notifications"],
                detail={
                    "priority": ["high", "urgent", "critical"]
                }
            )
        )
        high_priority_rule.add_target(log_target)

        # Add Slack notifier Lambda for high priority events
        if slack_notifier:
            high_priority_rule.add_target(
                targets.LambdaFunction(slack_notifier)
            )

        # Rule 4: S3 events (for file upload notifications)
        self.s3_events_rule = events.Rule(
            self,
            "S3EventsRule",
            rule_name=f"notifications-{environment}-s3-events",
            event_bus=self.event_bus,
            description="Route S3 bucket events",
            event_pattern=events.EventPattern(
                source=["aws.s3"],
                detail_type=["Object Created", "Object Deleted"]
            ),
            enabled=False  # Enable when S3 integration is ready
        )

        # Rule 5: Scheduled notification (daily standup reminder example)
        # NOTE: Scheduled rules MUST use the default event bus, not a custom event_bus
        self.scheduled_rule = events.Rule(
            self,
            "ScheduledNotificationRule",
            rule_name=f"notifications-{environment}-daily-standup",
            description="Daily standup reminder (9 AM weekdays Pacific Time)",
            schedule=events.Schedule.cron(
                minute="0",
                hour="17",  # 9 AM Pacific = 5 PM UTC (adjust for your timezone)
                week_day="MON-FRI",
                month="*",
                year="*"
            ),
            enabled=False  # Disabled by default, enable when Lambda is ready
        )

        # Add Slack notifier as target for scheduled events if provided
        if slack_notifier:
            self.scheduled_rule.add_target(
                targets.LambdaFunction(
                    slack_notifier,
                    event=events.RuleTargetInput.from_object({
                        "source": "custom.notifications",
                        "detail-type": "Scheduled Reminder",
                        "detail": {
                            "message": "Daily standup reminder",
                            "priority": "normal"
                        }
                    })
                )
            )

        # Rule 6: Error/failure events
        error_rule = events.Rule(
            self,
            "ErrorEventsRule",
            rule_name=f"notifications-{environment}-errors",
            event_bus=self.event_bus,
            description="Route error and failure events",
            event_pattern=events.EventPattern(
                source=["custom.notifications"],
                detail_type=["Error", "Failure", "Exception"]
            )
        )
        error_rule.add_target(log_target)

        # Send errors directly to Slack
        if slack_notifier:
            error_rule.add_target(
                targets.LambdaFunction(slack_notifier)
            )

        # Archive for event replay (useful for debugging and recovery)
        event_archive = events.Archive(
            self,
            "EventArchive",
            archive_name=f"notifications-service-{environment}-archive",
            source_event_bus=self.event_bus,
            description="Archive all events for replay and debugging",
            retention=Duration.days(7) if environment == "dev" else Duration.days(30),
            event_pattern=events.EventPattern(
                source=events.Match.prefix("")  # Archive all events
            )
        )

        # Dead Letter Queue for failed event processing (optional, for future use)
        dlq = sqs.Queue(
            self,
            "EventBridgeDLQ",
            queue_name=f"notifications-service-{environment}-dlq",
            retention_period=Duration.days(14),
            removal_policy=RemovalPolicy.DESTROY if environment == "dev" else RemovalPolicy.RETAIN
        )

        # Outputs
        CfnOutput(
            self,
            "EventBusName",
            value=self.event_bus.event_bus_name,
            description="Name of the custom event bus",
            export_name=f"NotificationService-{environment}-EventBusName"
        )

        CfnOutput(
            self,
            "EventBusArn",
            value=self.event_bus.event_bus_arn,
            description="ARN of the custom event bus",
            export_name=f"NotificationService-{environment}-EventBusArn"
        )

        CfnOutput(
            self,
            "CatchAllRuleName",
            value=catch_all_rule.rule_name,
            description="Name of the catch-all logging rule"
        )

        CfnOutput(
            self,
            "CustomEventsRuleName",
            value=self.custom_events_rule.rule_name,
            description="Name of the custom events rule"
        )

        CfnOutput(
            self,
            "HighPriorityRuleName",
            value=high_priority_rule.rule_name,
            description="Name of the high-priority events rule"
        )

        CfnOutput(
            self,
            "S3EventsRuleName",
            value=self.s3_events_rule.rule_name,
            description="Name of the S3 events rule"
        )

        CfnOutput(
            self,
            "ScheduledRuleName",
            value=self.scheduled_rule.rule_name,
            description="Name of the scheduled notification rule"
        )

        CfnOutput(
            self,
            "ErrorRuleName",
            value=error_rule.rule_name,
            description="Name of the error events rule"
        )

        CfnOutput(
            self,
            "EventArchiveName",
            value=event_archive.archive_name,
            description="Name of the event archive"
        )

        CfnOutput(
            self,
            "LogGroupName",
            value=self.log_group.log_group_name,
            description="CloudWatch log group for events"
        )

        CfnOutput(
            self,
            "DLQUrl",
            value=dlq.queue_url,
            description="Dead letter queue URL for failed events"
        )

        # Store references for use in other stacks
        self.high_priority_rule = high_priority_rule
        self.error_rule = error_rule
        self.dlq = dlq
