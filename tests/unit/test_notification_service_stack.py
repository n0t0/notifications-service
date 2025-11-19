import aws_cdk as core
import aws_cdk.assertions as assertions

from notification_service.notification_service_stack import NotificationServiceStack

# example tests. To run these tests, uncomment this file along with the example
# resource in notification_service/notification_service_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = NotificationServiceStack(app, "notification-service")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
