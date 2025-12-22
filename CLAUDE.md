# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Product Vision: Multi-Channel Notification Platform

**Primersky Notifications** - A production-ready, scalable event-driven notification service that enables businesses to send timely, relevant notifications across multiple channels.

### The Problem
- Businesses struggle to build reliable notification infrastructure
- Managing multiple channels (Slack, Email, SMS, Push) is complex
- Event-driven architectures require specialized expertise
- Scaling notification systems is expensive and time-consuming

### The Solution
A plug-and-play notification platform that:
- Receives events from any source (API, S3, Scheduled, Custom Apps)
- Routes intelligently using EventBridge rules
- Delivers to multiple channels (Slack, Email, SMS, Push)
- Scales automatically from 0 to millions of notifications
- Provides complete observability and retry logic

## Architecture

The project follows a multi-stack CDK architecture with explicit dependencies:

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│ API Gateway │────▶│  EventBridge │────▶│ Lambda Function │
└─────────────┘     │  Custom Bus  │     └─────────────────┘
                    │              │
┌─────────────┐     │              │     ┌─────────────────┐
│  S3 Events  │────▶│              │────▶│ Step Functions  │
└─────────────┘     │              │     └─────────────────┘
                    │              │
┌─────────────┐     │              │     ┌─────────────────┐
│  Scheduled  │────▶│              │────▶│ Multi-Channel   │
└─────────────┘     └──────────────┘     │ Notifier        │
                                         └─────────────────┘
```

### Stack Structure

1. **SQS Stack** (`notifications_service/sqs_stack.py`)
   - Creates the notification queue
   - Sets up EventBridge rule routing to SQS
   - Independent stack, deployed first

2. **Lambda Stack** (`notifications_service/lambda_stack.py`)
   - Creates three Lambda functions:
     - `slack_notifier`: Sends notifications to Slack
     - `event_processor`: Processes EventBridge events and invokes slack_notifier
     - `sqs_consumer`: Consumes messages from SQS queue and invokes slack_notifier
   - Depends on SQS Stack
   - Lambda functions reference each other via ARNs in environment variables

3. **EventBridge Stack** (`notifications_service/eventbridge_stack.py`)
   - Creates custom event bus and multiple routing rules:
     - Catch-all rule (dev only) for debugging
     - Custom events rule (routes to event_processor Lambda)
     - High-priority rule (routes to slack_notifier directly)
     - S3 events rule (disabled by default)
     - Scheduled rule (uses default event bus, disabled by default)
     - Error events rule (routes to slack_notifier)
   - Creates CloudWatch log group and event archive
   - Depends on Lambda Stack
   - **Important**: Scheduled rules MUST use the default event bus, not the custom event bus

4. **App Entry Point** (`app.py`)
   - Orchestrates stack creation
   - Manages environment configuration (dev/prod)
   - Sets stack dependencies: SQS → Lambda → EventBridge

## Development Roadmap

### Phase 1: Core Infrastructure ✅
- [x] EventBridge custom bus
- [x] Lambda functions (event_processor, slack_notifier, sqs_consumer)
- [x] SQS queue integration
- [x] Basic Slack notifications

### Phase 2: Multi-Channel Support
- [ ] Email notifications (SES integration)
- [ ] SMS notifications (SNS/Twilio)
- [ ] Push notifications (FCM/APNs)
- [ ] Webhook destinations

### Phase 3: Advanced Routing
- [ ] Content-based routing rules
- [ ] User preference management
- [ ] Rate limiting per channel
- [ ] Batch processing

### Phase 4: API & Dashboard
- [ ] REST API for event submission
- [ ] Admin dashboard (React)
- [ ] Template management
- [ ] Analytics & reporting

### Phase 5: Enterprise Features
- [ ] Multi-tenant support
- [ ] Custom event schemas
- [ ] Audit logging
- [ ] Compliance features (GDPR, SOC2)

## Pricing Model (Planned)

| Tier | Notifications/Month | Price | Features |
|------|---------------------|-------|----------|
| Free | 1,000 | $0 | Slack only, basic routing |
| Starter | 10,000 | $29 | + Email, priority support |
| Pro | 100,000 | $99 | + SMS, webhooks, analytics |
| Enterprise | Unlimited | $299+ | + SLA, dedicated support, custom |

## Development Commands

### Environment Setup
```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate.bat  # Windows

# Install dependencies
pip install -r requirements.txt

# Install Lambda function dependencies
cd lambda_functions/slack_notifier && pip install -r requirements.txt -t .
cd lambda_functions/event_processor && pip install -r requirements.txt -t .
cd lambda_functions/sqs_consumer && pip install -r requirements.txt -t .
```

### CDK Commands
```bash
# Synthesize CloudFormation template
cdk synth

# Show differences between deployed stack and current state
cdk diff

# Deploy all stacks (respects dependencies)
cdk deploy --all

# Deploy specific stack
cdk deploy NotificationsServiceSqs-dev

# Destroy all stacks
cdk destroy --all

# List all stacks
cdk ls
```

### Deployment Scripts
```bash
# Full deployment with checks
./deploy.sh

# Dry run (synth and diff only)
./deploy.sh --dry-run

# Destroy all stacks
./deploy.sh --destroy
```

### Testing
```bash
# Run unit tests
pytest tests/unit/

# Manual testing script
./tests/manual.sh

# Test EventBridge integration
./test-eventbridge.sh
```

## Configuration

### Environment Variables
The project uses environment context from `app.py`:
- `ENVIRONMENT`: Deployment environment (dev/prod)
- `CDK_DEFAULT_ACCOUNT` or `AWS_ACCOUNT_ID`: AWS account ID
- `CDK_DEFAULT_REGION` or `AWS_REGION`: AWS region (defaults to us-east-1)

Configuration is also stored in `.env` (NOT committed to git):
- Slack webhook URL
- Slack bot token
- AWS account and region
- Environment name

### CDK Context
Pass context values via command line:
```bash
cdk deploy -c environment=prod -c slack_webhook_url=https://hooks.slack.com/...
```

## Event Flow

- **EventBridge → Lambda**: Custom events go through event_processor, which decides whether to invoke slack_notifier
- **EventBridge → SQS → Lambda**: Events matching SQS rule go to queue, then consumed by sqs_consumer
- **Priority-based routing**: High-priority events bypass processing and go directly to slack_notifier

## API Usage Examples

### Send Notification via API
```bash
curl -X POST https://api.primersky.com/notifications \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "eventType": "order.created",
    "priority": "high",
    "channels": ["slack", "email"],
    "data": {
      "orderId": "12345",
      "customerId": "customer-1",
      "amount": 99.99
    },
    "template": "order-confirmation"
  }'
```

### Send Event via Python SDK
```python
from primersky_notifications import NotificationClient

client = NotificationClient(api_key="your-api-key")

client.send(
    event_type="order.created",
    priority="high",
    channels=["slack", "email"],
    data={
        "orderId": "12345",
        "customerId": "customer-1",
        "amount": 99.99
    }
)
```

### Direct EventBridge Integration
```python
import boto3
import json

events = boto3.client('events')

response = events.put_events(
    Entries=[
        {
            'Source': 'custom.myapp',
            'DetailType': 'Order Created',
            'Detail': json.dumps({
                'orderId': '12345',
                'customerId': 'customer-1',
                'amount': 99.99
            }),
            'EventBusName': 'notifications-service-dev-bus'
        }
    ]
)
```

## Lambda Function Structure

All Lambda functions follow the same pattern:
- Handler file: `handler.py` with `lambda_handler(event, context)` function
- Dependencies: `requirements.txt` in each function directory
- Runtime: Python 3.12
- Packaging: Dependencies must be installed in the function directory for deployment

## Important Implementation Details

### Stack Dependencies
The stacks have explicit dependencies set in `app.py`:
```python
lambda_stack.add_dependency(sqs_stack)
eventbridge_stack.add_dependency(lambda_stack)
```
This ensures proper deployment order and resource availability.

### Lambda Invocation Pattern
- `event_processor` and `sqs_consumer` invoke `slack_notifier` asynchronously using the Lambda client
- ARNs are passed via environment variables (`SLACK_NOTIFIER_ARN`)
- IAM permissions are granted using `grant_invoke()` method

### EventBridge Rules
- Custom event bus is used for application events
- Default event bus MUST be used for scheduled (cron) rules
- Event patterns use `events.Match.prefix("")` to match all events or specific values for filtering
- Rules can have multiple targets (CloudWatch Logs, Lambda, SQS)

### Environment-Specific Configuration
- **dev**: Shorter log retention (1 week), DESTROY removal policy, catch-all logging enabled
- **prod**: Longer retention (1 month), RETAIN removal policy, catch-all logging disabled

## Common Development Tasks

### Adding a New Event Type
1. Define event pattern in `notifications_service/eventbridge_stack.py`
2. Create or update EventBridge rule with appropriate filter
3. Add processing logic in `lambda_functions/event_processor/handler.py`
4. Update `should_notify_slack()` if Slack notification is needed

### Adding a New Lambda Function
1. Create new directory under `lambda_functions/`
2. Add `handler.py` and `requirements.txt`
3. Update `notifications_service/lambda_stack.py` to create the function
4. Grant necessary IAM permissions
5. Add function as target in EventBridge or SQS event source

### Modifying Stack Configuration
1. Update the relevant stack file in `notifications_service/`
2. Run `cdk diff` to preview changes
3. Run `cdk deploy` to apply changes
4. Check CloudFormation console for deployment status

## Troubleshooting

### Lambda Function Issues
- Check CloudWatch Logs: `/aws/lambda/notification-service-{env}-{function-name}`
- Verify environment variables are set correctly
- Ensure IAM permissions are granted
- Check function timeout and memory settings

### EventBridge Issues
- Check EventBridge CloudWatch logs: `/aws/events/notifications-service-{env}`
- Verify event pattern matches the incoming events
- Use event archive for replay and debugging
- Enable catch-all rule in dev to see all events

### Deployment Issues
- Ensure AWS credentials are configured
- Check CDK bootstrap in the target account/region
- Verify stack dependencies are correct
- Look for circular dependencies between stacks

## AWS Services Comparison

| Feature | Lambda | EventBridge | Step Functions |
|---------|--------|-------------|----------------|
| **Purpose** | Run code | Route events | Orchestrate workflows |
| **Execution** | Single function | Fan-out to multiple targets | Sequential/parallel steps |
| **State** | Stateless | Stateless | Stateful (tracks workflow progress) |
| **Duration** | Max 15 minutes | Instant routing | Up to 1 year |
| **Retry Logic** | Manual | Built-in per target | Built-in with error handling |
| **Pricing** | Per invocation + duration | Per event published | Per state transition |
| **Best For** | Single-purpose tasks | Event routing/fan-out | Multi-step workflows |

### When to Use Each

**Lambda** - Single-purpose functions:
- Process a single notification
- Transform data
- Call external API
- Handle webhook

**EventBridge** - Event routing and orchestration:
- Route notifications to multiple channels
- Filter events by pattern
- Schedule recurring tasks
- Connect AWS services

**Step Functions** - Complex workflows:
- Multi-step processes with branching
- Long-running workflows (hours/days)
- Human approval gates
- Retry/error handling with rollback
- Audit trail requirements

## Future Service Idea: Workflow Automation Service

A Step Functions-based service for complex business processes:

### Example Workflows

1. **User Onboarding Flow**
   - Create account → Verify email → Send welcome notification → Schedule follow-up

2. **Order Processing**
   - Validate order → Check inventory → Process payment → Notify warehouse → Send confirmation

3. **Approval Workflows**
   - Submit request → Manager approval → Finance approval → Execute → Notify all parties

4. **Scheduled Reports**
   - Gather data → Generate report → Store in S3 → Send via email → Archive

### Integration Points

- Triggers: API Gateway, EventBridge, S3, Scheduled
- Actions: Lambda, DynamoDB, SES, SNS, External APIs
- Notifications: Connect to notifications-service for multi-channel delivery
