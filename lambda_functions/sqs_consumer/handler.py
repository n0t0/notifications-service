"""
SQS Consumer Lambda Function

Processes notification messages from SQS queue.
Can batch process multiple messages and handle failures gracefully.
"""

import json
import os
import boto3
from datetime import datetime, timezone
from typing import Any, Dict, List

# Initialize AWS clients
lambda_client = boto3.client("lambda")


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    """
    Main handler for SQS message processing

    Receives batch of messages from SQS:
    {
        "Records": [
            {
                "messageId": "...",
                "body": "...",
                "attributes": {...},
                ...
            }
        ]
    }
    """
    print(f"Received {len(event.get('Records', []))} messages from SQS")

    successful_messages = []
    failed_messages = []

    for record in event.get("Records", []):
        try:
            # Process individual message
            result = process_message(record)
            successful_messages.append({
                "messageId": record.get("messageId"),
                "result": result
            })

        except Exception as e:
            print(f"Error processing message {record.get('messageId')}: {str(e)}")
            failed_messages.append({
                "messageId": record.get("messageId"),
                "error": str(e)
            })

    # Return batch processing results
    response = {
        "statusCode": 200 if not failed_messages else 207,  # 207 = Multi-Status
        "body": json.dumps({
            "processed": len(successful_messages),
            "failed": len(failed_messages),
            "successful_messages": successful_messages,
            "failed_messages": failed_messages
        })
    }

    # Return batch item failures for partial batch processing
    # SQS will retry only the failed messages
    if failed_messages:
        response["batchItemFailures"] = [
            {"itemIdentifier": msg["messageId"]} for msg in failed_messages
        ]

    print(f"Batch processing complete: {len(successful_messages)} succeeded, {len(failed_messages)} failed")

    return response


def process_message(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single SQS message
    """
    message_id = record.get("messageId")
    body = record.get("body")

    print(f"Processing message {message_id}")

    # Parse message body (could be JSON from EventBridge or plain text)
    try:
        message_data = json.loads(body)
    except json.JSONDecodeError:
        message_data = {"raw_message": body}

    # Extract notification details
    notification = extract_notification_details(message_data)

    # Perform business logic based on notification type
    result = handle_notification(notification)

    # Optionally send to Slack for high-priority notifications
    if should_notify_slack(notification):
        invoke_slack_notifier(notification)

    return {
        "messageId": message_id,
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "notification_type": notification.get("type", "unknown"),
        "result": result
    }


def extract_notification_details(message_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract notification details from message
    Handles both EventBridge format and custom formats
    """
    # Check if message is from EventBridge
    if "detail" in message_data:
        return {
            "type": message_data.get("detail-type", "unknown"),
            "source": message_data.get("source", "unknown"),
            "timestamp": message_data.get("timestamp") or message_data.get("time"),
            "details": message_data.get("detail", {})
        }

    # Handle custom message format
    return {
        "type": message_data.get("type", "notification"),
        "source": message_data.get("source", "sqs"),
        "timestamp": message_data.get("timestamp", datetime.now(timezone.utc).isoformat()),
        "details": message_data
    }


def handle_notification(notification: Dict[str, Any]) -> Dict[str, Any]:
    """
    Business logic for processing different notification types
    """
    notification_type = notification.get("type", "").lower()
    details = notification.get("details", {})

    print(f"Handling notification type: {notification_type}")

    # Route based on notification type
    if "user" in notification_type and "registered" in notification_type:
        return handle_user_registration(details)

    elif "order" in notification_type:
        return handle_order_notification(details)

    elif "payment" in notification_type:
        return handle_payment_notification(details)

    elif "error" in notification_type or "failure" in notification_type:
        return handle_error_notification(details)

    else:
        return handle_generic_notification(details)


def handle_user_registration(details: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle user registration notifications
    """
    user_id = details.get("userId") or details.get("user_id")
    email = details.get("email")

    print(f"Processing user registration: {user_id}")

    # Example: Trigger welcome email, setup user profile, etc.
    return {
        "action": "user_registered",
        "user_id": user_id,
        "email": email,
        "status": "processed"
    }


def handle_order_notification(details: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle order-related notifications
    """
    order_id = details.get("orderId") or details.get("order_id")

    print(f"Processing order notification: {order_id}")

    # Example: Update inventory, send confirmation, etc.
    return {
        "action": "order_processed",
        "order_id": order_id,
        "status": "processed"
    }


def handle_payment_notification(details: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle payment-related notifications
    """
    payment_id = details.get("paymentId") or details.get("payment_id")
    amount = details.get("amount")

    print(f"Processing payment notification: {payment_id}")

    # Example: Update payment records, trigger receipts, etc.
    return {
        "action": "payment_processed",
        "payment_id": payment_id,
        "amount": amount,
        "status": "processed"
    }


def handle_error_notification(details: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle error/failure notifications
    """
    error_message = details.get("message") or details.get("error")

    print(f"Processing error notification: {error_message}")

    # Example: Log to monitoring system, create incident, etc.
    return {
        "action": "error_logged",
        "error": error_message,
        "status": "processed"
    }


def handle_generic_notification(details: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle generic notifications
    """
    print(f"Processing generic notification: {json.dumps(details)}")

    return {
        "action": "generic_processed",
        "status": "processed"
    }


def should_notify_slack(notification: Dict[str, Any]) -> bool:
    """
    Determine if notification should be sent to Slack
    """
    details = notification.get("details", {})
    notification_type = notification.get("type", "").lower()

    # Check priority
    priority = details.get("priority", "normal").lower()
    if priority in ["high", "critical", "urgent"]:
        return True

    # Check for error/failure types
    if any(word in notification_type for word in ["error", "failure", "alert"]):
        return True

    return False


def invoke_slack_notifier(notification: Dict[str, Any]) -> None:
    """
    Invoke Slack notifier Lambda function
    """
    slack_notifier_arn = os.environ.get("SLACK_NOTIFIER_ARN")
    if not slack_notifier_arn:
        print("SLACK_NOTIFIER_ARN not configured, skipping Slack notification")
        return

    # Convert notification to EventBridge format for Slack notifier
    event_payload = {
        "source": notification.get("source", "custom.notifications"),
        "detail-type": notification.get("type", "Notification"),
        "detail": notification.get("details", {})
    }

    try:
        response = lambda_client.invoke(
            FunctionName=slack_notifier_arn,
            InvocationType="Event",  # Async invocation
            Payload=json.dumps(event_payload)
        )
        print(f"Slack notifier invoked: {response['StatusCode']}")

    except Exception as e:
        print(f"Failed to invoke Slack notifier: {str(e)}")
        # Don't raise - we don't want Slack failures to fail message processing
