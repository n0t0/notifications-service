#!/bin/bash
# Cleanup script for removing CDK infrastructure files

echo "Cleaning up CDK files from notifications-service repo..."

# Remove CDK-specific files
rm -f app.py
rm -f cdk.json
rm -f cdk.context.json
rm -f deploy.sh
rm -f source.bat
rm -rf cdk.out

# Remove old Lambda handlers (now in primersky-infra/lambda_functions/)
rm -rf lambda_functions/

# Remove old CDK stack files (now in primersky-infra/services/notifications_service.py)
rm -rf notifications_service/*.py
rm -rf notifications_service/__pycache__
# Keep the notifications_service directory for future application logic
mkdir -p notifications_service/channels
mkdir -p notifications_service/core
mkdir -p notifications_service/utils
touch notifications_service/__init__.py
touch notifications_service/channels/__init__.py
touch notifications_service/core/__init__.py
touch notifications_service/utils/__init__.py

echo "✅ Removed CDK files, Lambda handlers, and old stack files"

# Update requirements.txt to remove CDK dependencies
cat > requirements.txt << 'REQS'
boto3>=1.26.0
aws-lambda-powertools>=2.0.0
slack-sdk>=3.19.0
requests>=2.31.0
REQS

echo "✅ Updated requirements.txt (removed CDK dependencies)"

# Update README
cat > README.md << 'README'
# Notifications Service

Multi-channel notification service supporting Slack, Email, SMS, Teams, and App notifications.

## Architecture

This repository contains the **application logic** for the notifications service. Infrastructure (CDK) is managed in the [`primersky-infra`](https://github.com/n0t0/primersky-infra) repository.

**Pattern**: Similar to primersky-boro
- **Application logic**: Lives in this repo (`notifications_service/`)
- **Infrastructure (CDK)**: Lives in `primersky-infra` repo
- **Lambda handlers**: Lives in `primersky-infra/lambda_functions/`

## Project Structure

```
notifications_service/
├── channels/          # Notification channel implementations
│   ├── slack.py      # Slack integration
│   ├── email.py      # Email via SES
│   ├── sms.py        # SMS via SNS
│   └── teams.py      # Microsoft Teams
├── core/             # Core notification logic
│   ├── formatter.py  # Message formatting
│   ├── router.py     # Channel routing
│   └── templates.py  # Message templates
└── utils/            # Utility functions

tests/               # Unit tests
docs/                # Documentation
```

## Development

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Testing

```bash
pytest tests/
```

### Local Testing

See `test-lambda-setup.sh` and `test-eventbridge.sh` for examples of testing notification logic locally.

## Deployment

Infrastructure is deployed from `primersky-infra`:

```bash
cd ../primersky-infra
cdk deploy prod-Notifications-*
```

## Usage

### Send Slack Notification

```python
from notifications_service.channels.slack import SlackNotifier

notifier = SlackNotifier(webhook_url="https://hooks.slack.com/...")
notifier.send(
    message="Deployment completed",
    priority="high",
    details={"status": "success", "duration": "2m 30s"}
)
```

### Send Email

```python
from notifications_service.channels.email import EmailNotifier

notifier = EmailNotifier(region="us-west-2")
notifier.send(
    to="ivo@primersky.com",
    subject="Infrastructure Alert",
    message="Service health check failed"
)
```

## Infrastructure

All infrastructure (Lambda, SQS, EventBridge, API Gateway) is defined in:
- [`primersky-infra/services/notifications_service.py`](https://github.com/n0t0/primersky-infra/blob/main/services/notifications_service.py)
- [`primersky-infra/cdk_stacks/`](https://github.com/n0t0/primersky-infra/tree/main/cdk_stacks)

## API

The Notifications API is deployed via API Gateway:
- Production: `https://8kc0xkfbha.execute-api.us-west-2.amazonaws.com/prod`
- Endpoint: `POST /notifications`
- Auth: API key required (stored in AWS Secrets Manager)

See API documentation in `docs/API.md`
README

echo "✅ Updated README.md"

echo ""
echo "Cleanup complete! CDK-related files removed."
echo "This repo now contains only notification logic."
echo ""
echo "Next steps:"
echo "1. Review changes: git status"
echo "2. Commit: git add -A && git commit -m 'Remove CDK code - infrastructure moved to primersky-infra'"
echo "3. Push: git push"
