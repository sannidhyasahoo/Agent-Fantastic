#!/usr/bin/env python3
"""
Deploy Lambda Functions for VPC Flow Log Anomaly Detection System
"""
import boto3
import json
import zipfile
import os
from io import BytesIO

def create_lambda_function(lambda_client, function_name, handler, code, role_arn, description):
    """Create a Lambda function with inline code"""
    
    # Create zip file in memory
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr('lambda_function.py', code)
    zip_buffer.seek(0)
    
    try:
        response = lambda_client.create_function(
            FunctionName=function_name,
            Runtime='python3.9',
            Role=role_arn,
            Handler=handler,
            Code={'ZipFile': zip_buffer.read()},
            Description=description,
            Timeout=60,
            MemorySize=256,
            Environment={
                'Variables': {
                    'KINESIS_STREAM': 'vpc-flow-logs-stream',
                    'DYNAMODB_TABLE': 'threat-incidents'
                }
            }
        )
        print(f"✅ Created {function_name}: {response['FunctionArn']}")
        return response['FunctionArn']
    except lambda_client.exceptions.ResourceConflictException:
        print(f"✅ {function_name} already exists")
        return f"arn:aws:lambda:us-east-1:590183882900:function:{function_name}"
    except Exception as e:
        print(f"❌ Failed to create {function_name}: {e}")
        return None

def deploy_lambda_functions():
    """Deploy all Lambda functions for threat detection"""
    print("=== Deploying Lambda Functions ===")
    
    session = boto3.Session(
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        aws_session_token=os.getenv('AWS_SESSION_TOKEN'),
        region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    )
    
    lambda_client = session.client('lambda')
    iam_client = session.client('iam')
    
    # Create IAM role for Lambda functions
    role_name = 'VPCThreatDetectionLambdaRole'
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    try:
        role_response = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='Role for VPC Threat Detection Lambda functions'
        )
        role_arn = role_response['Role']['Arn']
        print(f"✅ Created IAM role: {role_arn}")
    except iam_client.exceptions.EntityAlreadyExistsException:
        role_arn = f"arn:aws:iam::590183882900:role/{role_name}"
        print(f"✅ Using existing IAM role: {role_arn}")
    
    # Attach policies
    policies = [
        'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole',
        'arn:aws:iam::aws:policy/AmazonKinesisReadOnlyAccess',
        'arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess',
        'arn:aws:iam::aws:policy/AmazonBedrockFullAccess'
    ]
    
    for policy in policies:
        try:
            iam_client.attach_role_policy(RoleName=role_name, PolicyArn=policy)
        except:
            pass  # Policy already attached
    
    # Lambda 1: VPC Threat Detector
    vpc_detector_code = '''
import json
import boto3
import re
from datetime import datetime

def lambda_handler(event, context):
    """Process VPC Flow Logs and detect threats"""
    
    dynamodb = boto3.client('dynamodb')
    
    threats_detected = []
    
    for record in event.get('Records', []):
        # Parse Kinesis record
        if 'kinesis' in record:
            data = json.loads(record['kinesis']['data'])
        else:
            data = record
        
        # Threat detection logic
        threat = detect_threat(data)
        if threat:
            # Store in DynamoDB
            incident_id = f"threat-{int(datetime.now().timestamp())}"
            
            dynamodb.put_item(
                TableName='threat-incidents',
                Item={
                    'incident_id': {'S': incident_id},
                    'timestamp': {'S': datetime.now().isoformat()},
                    'source_ip': {'S': threat.get('source_ip', 'unknown')},
                    'threat_type': {'S': threat['type']},
                    'severity': {'S': threat['severity']},
                    'confidence': {'N': str(threat['confidence'])},
                    'status': {'S': 'DETECTED'},
                    'raw_data': {'S': json.dumps(data)}
                }
            )
            
            threats_detected.append(threat)
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'threats_detected': len(threats_detected),
            'incidents': threats_detected
        })
    }

def detect_threat(flow_log):
    """Basic threat detection patterns"""
    
    # Port scanning detection
    if flow_log.get('dest_port') in [22, 23, 80, 443, 3389] and flow_log.get('bytes', 0) < 100:
        return {
            'type': 'port_scanning',
            'severity': 'HIGH',
            'confidence': 0.8,
            'source_ip': flow_log.get('source_ip')
        }
    
    # Crypto mining detection
    if flow_log.get('dest_port') in [4444, 8333, 9999]:
        return {
            'type': 'crypto_mining',
            'severity': 'CRITICAL',
            'confidence': 0.9,
            'source_ip': flow_log.get('source_ip')
        }
    
    # Data exfiltration detection
    if flow_log.get('bytes', 0) > 10000000:  # 10MB
        return {
            'type': 'data_exfiltration',
            'severity': 'HIGH',
            'confidence': 0.7,
            'source_ip': flow_log.get('source_ip')
        }
    
    return None
'''
    
    # Lambda 2: Threat Enrichment
    threat_enrichment_code = '''
import json
import boto3
from datetime import datetime

def lambda_handler(event, context):
    """Enrich threat data with additional context"""
    
    bedrock_runtime = boto3.client('bedrock-agent-runtime')
    dynamodb = boto3.client('dynamodb')
    
    for record in event.get('Records', []):
        # Get threat incident
        incident_id = record.get('incident_id')
        
        if incident_id:
            # Get incident details
            response = dynamodb.get_item(
                TableName='threat-incidents',
                Key={'incident_id': {'S': incident_id}}
            )
            
            if 'Item' in response:
                incident = response['Item']
                
                # Enrich with threat intelligence
                enrichment = get_threat_intelligence(incident)
                
                # Update incident with enrichment
                dynamodb.update_item(
                    TableName='threat-incidents',
                    Key={'incident_id': {'S': incident_id}},
                    UpdateExpression='SET enrichment = :enrichment, updated_at = :updated',
                    ExpressionAttributeValues={
                        ':enrichment': {'S': json.dumps(enrichment)},
                        ':updated': {'S': datetime.now().isoformat()}
                    }
                )
    
    return {'statusCode': 200, 'body': json.dumps('Enrichment complete')}

def get_threat_intelligence(incident):
    """Get threat intelligence for incident"""
    return {
        'geolocation': 'Unknown',
        'reputation': 'Suspicious',
        'threat_feeds': [],
        'similar_incidents': 0
    }
'''
    
    # Lambda 3: Agent Orchestrator
    agent_orchestrator_code = '''
import json
import boto3
from datetime import datetime

def lambda_handler(event, context):
    """Orchestrate Bedrock agents for threat analysis"""
    
    bedrock_runtime = boto3.client('bedrock-agent-runtime')
    
    # Agent IDs (from deployment)
    agents = {
        'threat_classifier': 'LB7W1ORPJG',
        'investigation': 'IHGZJIKZ8T', 
        'response_orchestration': 'W2JDG72L8B',
        'threat_intelligence': 'HLOGFAE8YI',
        'root_cause': 'LFKFNCTX3B'
    }
    
    results = {}
    
    for record in event.get('Records', []):
        threat_data = json.loads(record.get('body', '{}'))
        
        # Classify threat
        classification = invoke_agent(
            bedrock_runtime,
            agents['threat_classifier'],
            f"Classify this threat: {json.dumps(threat_data)}"
        )
        
        results['classification'] = classification
        
        # Get response recommendations
        response_plan = invoke_agent(
            bedrock_runtime,
            agents['response_orchestration'],
            f"Create response plan for: {json.dumps(threat_data)}"
        )
        
        results['response_plan'] = response_plan
    
    return {
        'statusCode': 200,
        'body': json.dumps(results)
    }

def invoke_agent(bedrock_runtime, agent_id, query):
    """Invoke Bedrock agent with query"""
    try:
        response = bedrock_runtime.invoke_agent(
            agentId=agent_id,
            agentAliasId='TSTALIASID',
            sessionId=f"session-{int(datetime.now().timestamp())}",
            inputText=query
        )
        
        # Process streaming response
        result = ""
        for event in response['completion']:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    result += chunk['bytes'].decode('utf-8')
        
        return result
    except Exception as e:
        return f"Error: {str(e)}"
'''
    
    # Deploy functions
    functions = [
        ('vpc-threat-detector', 'lambda_function.lambda_handler', vpc_detector_code, 'Detects threats from VPC Flow Logs'),
        ('threat-enrichment', 'lambda_function.lambda_handler', threat_enrichment_code, 'Enriches threat data with intelligence'),
        ('agent-orchestrator', 'lambda_function.lambda_handler', agent_orchestrator_code, 'Orchestrates Bedrock agents for analysis')
    ]
    
    deployed_functions = []
    
    for func_name, handler, code, description in functions:
        arn = create_lambda_function(lambda_client, func_name, handler, code, role_arn, description)
        if arn:
            deployed_functions.append((func_name, arn))
    
    print(f"\n✅ Deployed {len(deployed_functions)} Lambda functions")
    return deployed_functions

if __name__ == "__main__":
    deploy_lambda_functions()