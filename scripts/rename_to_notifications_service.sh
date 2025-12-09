#!/bin/bash

# Rename notification-service to notifications-service
# This script updates all references in the codebase

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "🔄 Renaming notification-service → notifications-service"
echo "========================================================"
echo ""

PROJECT_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs/2. AREA/code/python/projects/notification-service"

if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}❌ Project directory not found${NC}"
    exit 1
fi

cd "$PROJECT_DIR"

# Step 1: Update Python package name
echo "Step 1: Renaming Python package..."
if [ -d "notification_service" ]; then
    mv notification_service notifications_service
    echo -e "${GREEN}✓${NC} Renamed notification_service → notifications_service"
else
    echo -e "${YELLOW}⚠️  notification_service directory not found${NC}"
fi

# Step 2: Update imports in Python files
echo ""
echo "Step 2: Updating Python imports..."

find . -type f -name "*.py" -not -path "./.venv/*" -not -path "./cdk.out/*" -exec sed -i '' 's/from notification_service/from notifications_service/g' {} \;
find . -type f -name "*.py" -not -path "./.venv/*" -not -path "./cdk.out/*" -exec sed -i '' 's/notification_service\./notifications_service\./g' {} \;

echo -e "${GREEN}✓${NC} Updated Python imports"

# Step 3: Update stack names in app.py
echo ""
echo "Step 3: Updating stack names..."

sed -i '' 's/NotificationService-/NotificationsService-/g' app.py
sed -i '' 's/f"NotificationService/f"NotificationsService/g' app.py

echo -e "${GREEN}✓${NC} Updated stack names"

# Step 4: Update queue name in sqs_stack.py
echo ""
echo "Step 4: Updating SQS queue name..."

if [ -f "notifications_service/sqs_stack.py" ]; then
    sed -i '' 's/notification-service-queue/notifications-service-queue/g' notifications_service/sqs_stack.py
    echo -e "${GREEN}✓${NC} Updated queue name"
fi

# Step 5: Update Lambda function names
echo ""
echo "Step 5: Updating Lambda function names..."

if [ -f "notifications_service/lambda_stack.py" ]; then
    # Already has correct naming (notifications-dev-*)
    echo -e "${GREEN}✓${NC} Lambda names already correct"
fi

# Step 6: Update GitHub remote
echo ""
echo "Step 6: Updating Git remote..."

CURRENT_REMOTE=$(git remote get-url origin 2>/dev/null || echo "")

if [[ $CURRENT_REMOTE == *"notification-service"* ]]; then
    NEW_REMOTE=$(echo $CURRENT_REMOTE | sed 's/notification-service/notifications-service/')
    git remote set-url origin $NEW_REMOTE
    echo -e "${GREEN}✓${NC} Updated Git remote: $NEW_REMOTE"
    echo -e "${YELLOW}  ⚠️  Don't forget to rename repo on GitHub!${NC}"
    echo -e "${YELLOW}     https://github.com/n0t0/notification-service/settings${NC}"
else
    echo -e "${YELLOW}⚠️  Git remote already updated or not found${NC}"
fi

# Step 7: Clean CDK artifacts
echo ""
echo "Step 7: Cleaning CDK artifacts..."

rm -rf cdk.out/
echo -e "${GREEN}✓${NC} Removed cdk.out directory"

# Step 8: Update documentation
echo ""
echo "Step 8: Updating documentation..."

for file in *.md; do
    if [ -f "$file" ]; then
        sed -i '' 's/notification-service/notifications-service/g' "$file"
        sed -i '' 's/NotificationService/NotificationsService/g' "$file"
    fi
done

echo -e "${GREEN}✓${NC} Updated documentation files"

echo ""
echo "========================================================"
echo -e "${GREEN}✅ Rename complete!${NC}"
echo "========================================================"
echo ""
echo "📝 Summary of changes:"
echo "   • notification_service/ → notifications_service/"
echo "   • NotificationService* stacks → NotificationsService*"
echo "   • notification-service-queue → notifications-service-queue"
echo "   • Git remote updated"
echo ""
echo "🎯 Next steps:"
echo ""
echo "1. Rename GitHub repository:"
echo "   → Go to: https://github.com/n0t0/notification-service/settings"
echo "   → Change name to: notifications-service"
echo ""
echo "2. Update local directory name:"
echo "   cd .."
echo "   mv notification-service notifications-service"
echo "   cd notifications-service"
echo ""
echo "3. Destroy old stacks (if any deployed):"
echo "   cdk destroy NotificationService-dev"
echo "   cdk destroy NotificationServiceSqs-dev"
echo "   cdk destroy NotificationServiceEventBridge-dev"
echo "   cdk destroy NotificationServiceLambda-dev"
echo ""
echo "4. Verify new stack names:"
echo "   cdk list"
echo "   # Should show: NotificationsService-*"
echo ""
echo "5. Deploy with new names:"
echo "   cdk deploy --all"
echo ""
echo "6. Commit changes:"
echo "   git add -A"
echo "   git commit -m 'refactor: rename to notifications-service'"
echo "   git push"
echo ""
