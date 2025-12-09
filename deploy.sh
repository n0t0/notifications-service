#!/bin/bash
# Quick deployment script for notification service
# Usage: ./deploy.sh [--dry-run] [--destroy]

set -euo pipefail

YELLOW='\033[0;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

DRY_RUN=0
DESTROY=0

while [[ ${#} -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift;;
    --destroy) DESTROY=1; shift;;
    *) echo "Unknown arg: $1"; exit 2;;
  esac
done

echo -e "${YELLOW}Notification Service - CDK Deploy${NC}"
echo ""

# Check prerequisites
if ! command -v cdk &> /dev/null; then
  echo -e "${RED}✗ AWS CDK CLI not found. Install with: npm install -g aws-cdk${NC}"
  exit 1
fi

if ! command -v python3 &> /dev/null; then
  echo -e "${RED}✗ Python3 not found${NC}"
  exit 1
fi

if ! command -v aws &> /dev/null; then
  echo -e "${RED}✗ AWS CLI not found${NC}"
  exit 1
fi

# Install dependencies
echo -e "${YELLOW}Installing Node dependencies...${NC}"
npm install

echo -e "${YELLOW}Installing Python dependencies...${NC}"
pip install -r requirements.txt

# Synthesize template
echo -e "${YELLOW}Synthesizing CloudFormation template...${NC}"
cdk synth

# Show diff
echo -e "${YELLOW}Changes to be deployed:${NC}"
cdk diff

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo -e "${GREEN}✓ Dry-run complete. No changes applied.${NC}"
  exit 0
fi

if [[ "$DESTROY" -eq 1 ]]; then
  echo -e "${RED}Destroying stack...${NC}"
  cdk destroy --force
  echo -e "${GREEN}✓ Stack destroyed${NC}"
  exit 0
fi

# Deploy
echo ""
echo -e "${YELLOW}Deploying stack...${NC}"
cdk deploy --require-approval=manual

echo -e "${GREEN}✓ Deployment complete!${NC}"
echo ""
echo -e "${YELLOW}Stack Outputs:${NC}"
aws cloudformation describe-stacks \
  --stack-name NotificationServiceStack \
  --query 'Stacks[0].Outputs' \
  --output table

echo ""
echo -e "${YELLOW}To test the deployment, run:${NC}"
echo "  bash test-eventbridge.sh"
