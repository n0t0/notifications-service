#!/usr/bin/env python3
"""
Notifications Service - CDK Application Entry Point

This app defines all stacks for the notifications service.
"""

import os
import aws_cdk as cdk

# Import from notification_service package (note: singular, matching your directory name)
from notification_service.notification_service_stack import NotificationServiceStack
from notification_service.eventbridge_stack import EventBridgeStack

# Get environment from context or environment variable
app = cdk.App()

# Get configuration
environment = app.node.try_get_context("environment") or os.getenv("ENVIRONMENT", "dev")
aws_account = os.getenv("CDK_DEFAULT_ACCOUNT") or os.getenv("AWS_ACCOUNT_ID")
aws_region = os.getenv("CDK_DEFAULT_REGION") or os.getenv("AWS_REGION", "us-east-1")

# Define environment
env = cdk.Environment(
    account=aws_account,
    region=aws_region
)

# Stack 1: Original Notification Service (SQS-based)
notification_stack = NotificationServiceStack(
    app,
    f"NotificationService-{environment}",
    env=env,
    description=f"Notification service with SQS ({environment})",
    tags={
        "Project": "NotificationService",
        "Environment": environment,
        "ManagedBy": "CDK",
        "Stack": "SQS"
    }
)

# Stack 2: EventBridge Stack (enhanced event routing)
eventbridge_stack = EventBridgeStack(
    app,
    f"NotificationServiceEventBridge-{environment}",
    env=env,
    description=f"EventBridge infrastructure for notifications service ({environment})",
    tags={
        "Project": "NotificationService",
        "Environment": environment,
        "ManagedBy": "CDK",
        "Stack": "EventBridge"
    }
)

# Synthesize the CloudFormation templates
app.synth()
