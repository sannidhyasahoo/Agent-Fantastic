# Quick Fix Guide - Get System Working

## 🚨 Current Issue: AWS Credentials Expired

Your AWS session tokens have expired. Here's how to fix it quickly:

## Step 1: Get Fresh AWS Credentials

### Option A: AWS Console (Recommended)
1. Go to **AWS Console**
2. Click your **username** (top right)
3. Select **"Command line or programmatic access"**
4. Copy credentials from **Option 2**
5. Set in PowerShell:

```powershell
$Env:AWS_ACCESS_KEY_ID="ASIA..."
$Env:AWS_SECRET_ACCESS_KEY="your_secret_key"
$Env:AWS_SESSION_TOKEN="IQoJb3JpZ2luX2VjE..."
$Env:AWS_DEFAULT_REGION="us-east-1"
```

### Option B: AWS CLI (If configured)
```powershell
aws sts get-caller-identity
# If this works, your CLI credentials are valid
```

## Step 2: Test Connection

```powershell
python testing/test-credentials.py
```

Expected output:
```
✅ AWS Connection Successful
Account ID: 590183882900
✅ Kinesis access: OK
✅ DynamoDB access: OK
✅ Bedrock access: OK
```

## Step 3: Test Basic System

```powershell
# Test data ingestion
python testing/basic-test.py

# Test threat detection pipeline
python testing/quick-test.py
```

## Step 4: Test Bedrock Agents

```powershell
# Test AI agents (once credentials work)
python deployment/simple-agent-test.py
```

## What Should Work After Fix

### ✅ Immediate Capabilities:
- **Data Ingestion**: Send VPC flow logs to Kinesis
- **Data Storage**: Store threats in DynamoDB
- **AI Analysis**: Use Bedrock agents for threat classification
- **Basic Testing**: Validate system components

### 🔧 Still Need Deployment:
- **Automated Processing**: Lambda functions for real-time processing
- **ML Models**: SageMaker for behavioral analysis
- **Orchestration**: Step Functions for workflow automation
- **Full Integration**: Complete end-to-end pipeline

## Quick Demo Script

Once credentials are fixed, run this for a quick demo:

```powershell
# 1. Test infrastructure
python testing/basic-test.py

# 2. Send test threat data
python testing/quick-test.py

# 3. Test AI agent analysis
python deployment/simple-agent-test.py
```

## Expected Results

### Infrastructure Test:
```
✅ Kinesis Stream: Operational
✅ DynamoDB Table: Operational
✅ Basic Threat Detection: Functional
```

### Threat Detection Test:
```
✅ Port scan test data sent
✅ Crypto mining test data sent
✅ Data stored in DynamoDB
```

### AI Agent Test:
```
✅ ThreatClassifierAgent is working!
Response: This appears to be reconnaissance activity with HIGH risk level...
```

## Time Estimate

- **Fix credentials**: 2-3 minutes
- **Test system**: 5-10 minutes
- **Demo ready**: 15 minutes total

## If Still Having Issues

### Common Problems:
1. **"Unable to locate credentials"** → Set environment variables correctly
2. **"Access Denied"** → Check IAM permissions
3. **"Region not found"** → Ensure AWS_DEFAULT_REGION is set
4. **"Service not available"** → Check service availability in us-east-1

### Debug Commands:
```powershell
# Check environment variables
echo $Env:AWS_ACCESS_KEY_ID
echo $Env:AWS_DEFAULT_REGION

# Test basic AWS access
aws sts get-caller-identity

# Check Bedrock access
aws bedrock list-foundation-models --region us-east-1
```

The system is 80% ready - just needs fresh credentials to demonstrate AI-powered threat detection capabilities!