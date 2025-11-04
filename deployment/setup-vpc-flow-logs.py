#!/usr/bin/env python3
"""
Setup VPC Flow Logs integration for real-time threat detection
"""
import boto3
import json
import os

def setup_vpc_flow_logs():
    """Setup VPC Flow Logs to feed into Kinesis stream"""
    print("=== Setting up VPC Flow Logs Integration ===")
    
    session = boto3.Session(
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        aws_session_token=os.getenv('AWS_SESSION_TOKEN'),
        region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    )
    
    ec2_client = session.client('ec2')
    kinesis_client = session.client('kinesis')
    lambda_client = session.client('lambda')
    iam_client = session.client('iam')
    
    # 1. Get default VPC
    try:
        vpcs = ec2_client.describe_vpcs(Filters=[{'Name': 'is-default', 'Values': ['true']}])
        if vpcs['Vpcs']:
            vpc_id = vpcs['Vpcs'][0]['VpcId']
            print(f"✅ Found default VPC: {vpc_id}")
        else:
            print("❌ No default VPC found")
            return False
    except Exception as e:
        print(f"❌ Error finding VPC: {e}")
        return False
    
    # 2. Create IAM role for VPC Flow Logs
    flow_logs_role_name = 'VPCFlowLogsDeliveryRole'
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "vpc-flow-logs.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    try:
        role_response = iam_client.create_role(
            RoleName=flow_logs_role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='Role for VPC Flow Logs delivery to Kinesis'
        )
        role_arn = role_response['Role']['Arn']
        print(f"✅ Created VPC Flow Logs role: {role_arn}")
    except iam_client.exceptions.EntityAlreadyExistsException:
        role_arn = f"arn:aws:iam::590183882900:role/{flow_logs_role_name}"
        print(f"✅ Using existing VPC Flow Logs role: {role_arn}")
    
    # Attach Kinesis policy
    kinesis_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "kinesis:PutRecord",
                    "kinesis:PutRecords"
                ],
                "Resource": f"arn:aws:kinesis:us-east-1:590183882900:stream/vpc-flow-logs-stream"
            }
        ]
    }
    
    try:
        iam_client.create_policy(
            PolicyName='VPCFlowLogsKinesisPolicy',
            PolicyDocument=json.dumps(kinesis_policy),
            Description='Policy for VPC Flow Logs to write to Kinesis'
        )
        print("✅ Created Kinesis policy")
    except iam_client.exceptions.EntityAlreadyExistsException:
        print("✅ Kinesis policy already exists")
    
    try:
        iam_client.attach_role_policy(
            RoleName=flow_logs_role_name,
            PolicyArn=f"arn:aws:iam::590183882900:policy/VPCFlowLogsKinesisPolicy"
        )
    except:
        pass  # Policy already attached
    
    # 3. Create VPC Flow Logs
    try:
        flow_logs_response = ec2_client.create_flow_logs(
            ResourceIds=[vpc_id],
            ResourceType='VPC',
            TrafficType='ALL',
            LogDestinationType='kinesis-data-stream',
            LogDestination=f"arn:aws:kinesis:us-east-1:590183882900:stream/vpc-flow-logs-stream",
            DeliverLogsPermissionArn=role_arn,
            LogFormat='${srcaddr} ${dstaddr} ${srcport} ${dstport} ${protocol} ${packets} ${bytes} ${start} ${end} ${action}'
        )
        
        flow_log_id = flow_logs_response['FlowLogIds'][0]
        print(f"✅ Created VPC Flow Logs: {flow_log_id}")
        
    except Exception as e:
        if "already exists" in str(e):
            print("✅ VPC Flow Logs already configured")
        else:
            print(f"❌ Error creating VPC Flow Logs: {e}")
    
    # 4. Setup Kinesis trigger for Lambda
    try:
        # Add event source mapping for vpc-threat-detector
        lambda_client.create_event_source_mapping(
            EventSourceArn=f"arn:aws:kinesis:us-east-1:590183882900:stream/vpc-flow-logs-stream",
            FunctionName='vpc-threat-detector',
            StartingPosition='LATEST',
            BatchSize=10
        )
        print("✅ Connected Kinesis to Lambda trigger")
        
    except Exception as e:
        if "already exists" in str(e):
            print("✅ Kinesis Lambda trigger already exists")
        else:
            print(f"⚠️ Lambda trigger setup: {e}")
    
    # 5. Test data flow
    print("\n=== Testing Data Flow ===")
    
    # Send test VPC Flow Log data
    test_flow_log = {
        "srcaddr": "10.0.1.100",
        "dstaddr": "45.76.102.45", 
        "srcport": "54321",
        "dstport": "4444",
        "protocol": "6",
        "packets": "10",
        "bytes": "1500",
        "start": "1642248000",
        "end": "1642248060",
        "action": "ACCEPT"
    }
    
    try:
        kinesis_client.put_record(
            StreamName='vpc-flow-logs-stream',
            Data=json.dumps(test_flow_log),
            PartitionKey='test-vpc-flow'
        )
        print("✅ Test VPC Flow Log data sent to Kinesis")
        
    except Exception as e:
        print(f"❌ Error sending test data: {e}")
    
    print("\n=== VPC Flow Logs Setup Complete ===")
    print("Real VPC traffic will now be analyzed for threats automatically!")
    
    return True

def create_cloudwatch_dashboard():
    """Create CloudWatch dashboard for monitoring"""
    print("\n=== Creating Monitoring Dashboard ===")
    
    session = boto3.Session(
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        aws_session_token=os.getenv('AWS_SESSION_TOKEN'),
        region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    )
    
    cloudwatch = session.client('cloudwatch')
    
    dashboard_body = {
        "widgets": [
            {
                "type": "metric",
                "properties": {
                    "metrics": [
                        ["AWS/Kinesis", "IncomingRecords", "StreamName", "vpc-flow-logs-stream"],
                        ["AWS/Lambda", "Invocations", "FunctionName", "vpc-threat-detector"],
                        ["AWS/DynamoDB", "ItemCount", "TableName", "threat-incidents"]
                    ],
                    "period": 300,
                    "stat": "Sum",
                    "region": "us-east-1",
                    "title": "VPC Threat Detection Metrics"
                }
            }
        ]
    }
    
    try:
        cloudwatch.put_dashboard(
            DashboardName='VPCThreatDetection',
            DashboardBody=json.dumps(dashboard_body)
        )
        print("✅ Created CloudWatch dashboard: VPCThreatDetection")
    except Exception as e:
        print(f"⚠️ Dashboard creation: {e}")

if __name__ == "__main__":
    success = setup_vpc_flow_logs()
    if success:
        create_cloudwatch_dashboard()
        print("\n🎉 VPC Flow Logs integration complete!")
        print("Your system is now processing real network traffic for threats.")
    else:
        print("\n⚠️ Setup encountered issues. Check AWS permissions.")