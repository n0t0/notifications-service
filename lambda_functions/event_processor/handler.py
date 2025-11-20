"""
Event Processor Lambda Function

Processes custom events from EventBridge and routes them appropriately.
Can invoke other Lambda functions, store data, or trigger workflows.
"""

import json
import os
import boto3
from datetime import datetime
from typing import Any, Dict


# Initialize AWS clients
lambda_client = boto3.client("lambda")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main handler for event processing
    """
    print(f"Processing event: {json.dumps(event)}")

    try:
        # Extract event details
        detail = event.get("detail", {})
        source = event.get("source", "unknown")
        detail_type = event.get("detail-type", "unknown")

        # Process based on event type
        result = process_event(detail, source, detail_type)

        # Check if we should notify Slack
        if should_notify_slack(detail, detail_type):
            notify_slack(event)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Event processed successfully",
                "source": source,
                "type": detail_type,
                "result": result
            })
        }

    except Exception as e:
        print(f"Error processing event: {str(e)}")

        # Send error to Slack
        send_error_notification(event, str(e))

        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }


def process_event(detail: Dict[str, Any], source: str, detail_type: str) -> Dict[str, Any]:
    """
    Process event based on type
    """

    print(f"Processing {detail_type} event from {source}")

    # Example processing logic - extend this for your use cases
    processing_result = {
        "processed_at": datetime.utcnow().isoformat(),
        "source": source,
        "type": detail_type,
    }

    # Add custom processing logic here
    if detail_type == "User Registered":
        processing_result["action"] = "send_welcome_email"
        processing_result["user"] = detail.get("userId")

    elif detail_type == "Order Created":
        processing_result["action"] = "process_order"
        processing_result["order_id"] = detail.get("orderId")

    elif detail_type == "Payment Failed":
        processing_result["action"] = "notify_support"
        processing_result["amount"] = detail.get("amount")

    else:
        processing_result["action"] = "log_event"

    print(f"Processing result: {json.dumps(processing_result)}")

    return processing_result


def should_notify_slack(detail: Dict[str, Any], detail_type: str) -> bool:
    """
    Determine if this event should trigger a Slack notification
    """

    # Always notify for high priority events
    priority = detail.get("priority", "normal")
    if priority in ["high", "critical", "urgent"]:
        return True

    # Notify for specific event types
    notify_types = [
        "Error",
        "Failure",
        "Payment Failed",
        "Security Alert",
    ]

    return detail_type in notify_types


def notify_slack(event: Dict[str, Any]) -> None:
    """
    Invoke Slack notifier Lambda
    """

    slack_notifier_arn = os.environ.get("SLACK_NOTIFIER_ARN")
    if not slack_notifier_arn:
        print("SLACK_NOTIFIER_ARN not configured, skipping Slack notification")
        return

    try:
        response = lambda_client.invoke(
            FunctionName=slack_notifier_arn,
            InvocationType="Event",  # Async invocation
            Payload=json.dumps(event)
        )
        print(f"Slack notifier invoked: {response['StatusCode']}")

    except Exception as e:
        print(f"Failed to invoke Slack notifier: {str(e)}")


def send_error_notification(event: Dict[str, Any], error: str) -> None:
    """
    Send error notification to Slack
    """

    error_event = {
        "source": "custom.notifications",
        "detail-type": "Error",
        "detail": {
            "message": f"Event processing failed: {error}",
            "priority": "high",
            "error": error,
            "original_event": event.get("detail-type", "unknown"),
            "timestamp": datetime.utcnow().isoformat()
        }
    }

    notify_slack(error_event)
