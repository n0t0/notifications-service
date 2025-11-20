"""
Slack Notifier Lambda Function

Sends formatted notifications to Slack using Incoming Webhooks.
Supports rich formatting, colors, and custom fields.
"""

import json
import os
import urllib3
from datetime import datetime, timezone
from typing import Any, Dict, List

# Initialize HTTP client
http = urllib3.PoolManager()


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    """
    Main handler for Slack notifications

    Expects event structure from EventBridge:
    {
        "source": "custom.notifications",
        "detail-type": "...",
        "detail": {
            "message": "...",
            "priority": "normal|high|critical",
            ...
        }
    }
    """
    print(f"Received event: {json.dumps(event)}")

    # Get Slack webhook URL from environment
    slack_webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not slack_webhook_url:
        print("ERROR: SLACK_WEBHOOK_URL environment variable not set")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Slack webhook URL not configured"})
        }

    try:
        # Build Slack message
        slack_message = build_slack_message(event)

        # Send to Slack
        response = send_to_slack(slack_webhook_url, slack_message)

        print(f"Slack notification sent successfully: {response}")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Notification sent to Slack",
                "detail_type": event.get("detail-type", "unknown")
            })
        }

    except Exception as e:
        print(f"Error sending Slack notification: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }


def build_slack_message(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build Slack message with rich formatting
    """
    detail = event.get("detail", {})
    source = event.get("source", "unknown")
    detail_type = event.get("detail-type", "Notification")

    # Determine color based on priority or event type
    color = get_message_color(detail, detail_type)

    # Build main message text
    message_text = detail.get("message", "No message provided")

    # Build fields for additional context
    fields = build_fields(detail, source, detail_type)

    # Construct Slack message
    slack_message = {
        "text": f"*{detail_type}*",
        "attachments": [
            {
                "color": color,
                "text": message_text,
                "fields": fields,
                "footer": "Notification Service",
                "footer_icon": "https://platform.slack-edge.com/img/default_application_icon.png",
                "ts": int(datetime.now(timezone.utc).timestamp())
            }
        ]
    }

    # Add username and icon if configured
    bot_name = os.environ.get("SLACK_BOT_NAME", "Notification Bot")
    slack_message["username"] = bot_name

    return slack_message


def get_message_color(detail: Dict[str, Any], detail_type: str) -> str:
    """
    Determine message color based on priority or type
    """
    priority = detail.get("priority", "normal").lower()

    # Priority-based colors
    if priority in ["critical", "urgent"]:
        return "danger"  # Red
    elif priority == "high":
        return "warning"  # Orange

    # Type-based colors
    if any(word in detail_type.lower() for word in ["error", "failure", "failed"]):
        return "danger"  # Red
    elif any(word in detail_type.lower() for word in ["warning", "alert"]):
        return "warning"  # Orange
    elif any(word in detail_type.lower() for word in ["success", "completed"]):
        return "good"  # Green

    return "#36a64f"  # Default blue-green


def build_fields(detail: Dict[str, Any], source: str, _detail_type: str) -> List[Dict[str, Any]]:
    """
    Build Slack message fields from event details
    """
    fields = []

    # Add source
    fields.append({
        "title": "Source",
        "value": source,
        "short": True
    })

    # Add priority if present
    priority = detail.get("priority")
    if priority:
        fields.append({
            "title": "Priority",
            "value": priority.upper(),
            "short": True
        })

    # Add timestamp if present
    timestamp = detail.get("timestamp")
    if timestamp:
        fields.append({
            "title": "Timestamp",
            "value": timestamp,
            "short": True
        })

    # Add custom fields from detail
    excluded_keys = {"message", "priority", "timestamp"}
    for key, value in detail.items():
        if key not in excluded_keys and not key.startswith("_"):
            # Format the field name (convert snake_case to Title Case)
            field_name = key.replace("_", " ").title()

            # Convert value to string if not already
            field_value = str(value) if not isinstance(value, str) else value

            fields.append({
                "title": field_name,
                "value": field_value,
                "short": len(field_value) < 40  # Short if value is brief
            })

    return fields


def send_to_slack(webhook_url: str, message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send message to Slack via webhook
    """
    encoded_message = json.dumps(message).encode('utf-8')

    response = http.request(
        'POST',
        webhook_url,
        body=encoded_message,
        headers={'Content-Type': 'application/json'}
    )

    if response.status != 200:
        raise Exception(
            f"Slack API error: {response.status} - {response.data.decode('utf-8')}"
        )

    return {
        "status": response.status,
        "response": response.data.decode('utf-8')
    }


def format_code_block(text: str) -> str:
    """
    Format text as Slack code block
    """
    return f"```{text}```"


def format_inline_code(text: str) -> str:
    """
    Format text as inline code
    """
    return f"`{text}`"
