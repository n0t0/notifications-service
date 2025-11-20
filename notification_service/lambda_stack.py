"""
Lambda Stack for Notifications Service

This stack creates:
- Slack Notifier Lambda function
- Event Processor Lambda function
- SQS Consumer Lambda function
- IAM roles and permissions
- CloudWatch log groups
- Integration with EventBridge and SQS
"""

from aws_cdk import (
    Stack,
    Duration,
    CfnOutput,
    RemovalPolicy,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_logs as logs,
    aws_sqs as sqs,
    aws_events as events,
    aws_lambda_event_sources as lambda_event_sources,
)
from constructs import Construct


class LambdaStack(Stack):
    """
    Lambda Stack - Serverless compute for notification processing
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        event_bus: events.IEventBus,
        notification_queue: sqs.IQueue,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get environment from context
        environment = self.node.try_get_context("environment") or "dev"

        # Get Slack webhook URL from context (will be stored in environment variable)
        slack_webhook_url = self.node.try_get_context("slack_webhook_url") or ""

        # ===== 1. SLACK NOTIFIER LAMBDA =====
        self.slack_notifier = self._create_slack_notifier(
            environment,
            slack_webhook_url
        )

        # ===== 2. EVENT PROCESSOR LAMBDA =====
        self.event_processor = self._create_event_processor(
            environment,
            self.slack_notifier
        )

        # ===== 3. SQS CONSUMER LAMBDA =====
        self.sqs_consumer = self._create_sqs_consumer(
            environment,
            notification_queue,
            self.slack_notifier
        )

        # ===== OUTPUTS =====
        self._create_outputs(construct_id)

    def _create_slack_notifier(
        self,
        environment: str,
        slack_webhook_url: str
    ) -> lambda_.Function:
        """
        Create Slack Notifier Lambda function
        """
        # CloudWatch Log Group
        log_group = logs.LogGroup(
            self,
            "SlackNotifierLogGroup",
            log_group_name=f"/aws/lambda/notification-service-{environment}-slack-notifier",
            retention=logs.RetentionDays.ONE_WEEK if environment == "dev" else logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY if environment == "dev" else RemovalPolicy.RETAIN
        )

        # Lambda Function
        slack_notifier = lambda_.Function(
            self,
            "SlackNotifier",
            function_name=f"notification-service-{environment}-slack-notifier",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("lambda_functions/slack_notifier"),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "SLACK_WEBHOOK_URL": slack_webhook_url,
                "SLACK_BOT_NAME": "Notification Bot",
                "ENVIRONMENT": environment,
                "LOG_LEVEL": "INFO" if environment == "prod" else "DEBUG"
            },
            log_group=log_group,
            description="Sends formatted notifications to Slack"
        )

        return slack_notifier

    def _create_event_processor(
        self,
        environment: str,
        slack_notifier: lambda_.Function
    ) -> lambda_.Function:
        """
        Create Event Processor Lambda function
        """
        # CloudWatch Log Group
        log_group = logs.LogGroup(
            self,
            "EventProcessorLogGroup",
            log_group_name=f"/aws/lambda/notification-service-{environment}-event-processor",
            retention=logs.RetentionDays.ONE_WEEK if environment == "dev" else logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY if environment == "dev" else RemovalPolicy.RETAIN
        )

        # Lambda Function
        event_processor = lambda_.Function(
            self,
            "EventProcessor",
            function_name=f"notification-service-{environment}-event-processor",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("lambda_functions/event_processor"),
            timeout=Duration.seconds(60),
            memory_size=512,
            environment={
                "SLACK_NOTIFIER_ARN": slack_notifier.function_arn,
                "ENVIRONMENT": environment,
                "LOG_LEVEL": "INFO" if environment == "prod" else "DEBUG"
            },
            log_group=log_group,
            description="Processes custom events from EventBridge"
        )

        # Grant permission to invoke Slack notifier
        slack_notifier.grant_invoke(event_processor)

        return event_processor

    def _create_sqs_consumer(
        self,
        environment: str,
        notification_queue: sqs.IQueue,
        slack_notifier: lambda_.Function
    ) -> lambda_.Function:
        """
        Create SQS Consumer Lambda function
        """
        # CloudWatch Log Group
        log_group = logs.LogGroup(
            self,
            "SqsConsumerLogGroup",
            log_group_name=f"/aws/lambda/notification-service-{environment}-sqs-consumer",
            retention=logs.RetentionDays.ONE_WEEK if environment == "dev" else logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY if environment == "dev" else RemovalPolicy.RETAIN
        )

        # Lambda Function
        sqs_consumer = lambda_.Function(
            self,
            "SqsConsumer",
            function_name=f"notification-service-{environment}-sqs-consumer",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("lambda_functions/sqs_consumer"),
            timeout=Duration.seconds(60),
            memory_size=512,
            environment={
                "SLACK_NOTIFIER_ARN": slack_notifier.function_arn,
                "ENVIRONMENT": environment,
                "LOG_LEVEL": "INFO" if environment == "prod" else "DEBUG"
            },
            log_group=log_group,
            description="Processes notification messages from SQS queue",
            # Enable partial batch failure reporting
            reserved_concurrent_executions=10 if environment == "prod" else None
        )

        # Grant permission to invoke Slack notifier
        slack_notifier.grant_invoke(sqs_consumer)

        # Add SQS as event source
        sqs_consumer.add_event_source(
            lambda_event_sources.SqsEventSource(
                notification_queue,
                batch_size=10,  # Process up to 10 messages at once
                max_batching_window=Duration.seconds(5),  # Wait up to 5 seconds to fill batch
                report_batch_item_failures=True  # Enable partial batch failure reporting
            )
        )

        # Grant permission to read from SQS queue
        notification_queue.grant_consume_messages(sqs_consumer)

        return sqs_consumer

    def _create_outputs(self, construct_id: str) -> None:
        """
        Create CloudFormation outputs
        """
        # Slack Notifier outputs
        CfnOutput(
            self,
            "SlackNotifierFunctionName",
            value=self.slack_notifier.function_name,
            description="Name of the Slack Notifier Lambda function",
            export_name=f"{construct_id}-SlackNotifierName"
        )

        CfnOutput(
            self,
            "SlackNotifierFunctionArn",
            value=self.slack_notifier.function_arn,
            description="ARN of the Slack Notifier Lambda function",
            export_name=f"{construct_id}-SlackNotifierArn"
        )

        # Event Processor outputs
        CfnOutput(
            self,
            "EventProcessorFunctionName",
            value=self.event_processor.function_name,
            description="Name of the Event Processor Lambda function",
            export_name=f"{construct_id}-EventProcessorName"
        )

        CfnOutput(
            self,
            "EventProcessorFunctionArn",
            value=self.event_processor.function_arn,
            description="ARN of the Event Processor Lambda function",
            export_name=f"{construct_id}-EventProcessorArn"
        )

        # SQS Consumer outputs
        CfnOutput(
            self,
            "SqsConsumerFunctionName",
            value=self.sqs_consumer.function_name,
            description="Name of the SQS Consumer Lambda function",
            export_name=f"{construct_id}-SqsConsumerName"
        )

        CfnOutput(
            self,
            "SqsConsumerFunctionArn",
            value=self.sqs_consumer.function_arn,
            description="ARN of the SQS Consumer Lambda function",
            export_name=f"{construct_id}-SqsConsumerArn"
        )
