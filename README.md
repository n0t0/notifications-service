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

lambda_functions/     # Lambda handler examples (deployed from primersky-infra)
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
