#!/usr/bin/env python3
"""
Complete System Status Check for VPC Flow Log Anomaly Detection System
Checks all AWS services, connections, and missing components
"""
import boto3
import json
import os
from datetime import datetime

def check_system_status():
    """Comprehensive system status check"""
    print("=== VPC Flow Log Anomaly Detection System Status Check ===")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    # Configure AWS session
    session = boto3.Session(
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        aws_session_token=os.getenv('AWS_SESSION_TOKEN'),
        region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    )
    
    status_report = {
        "aws_services": {},
        "bedrock_agents": {},
        "infrastructure": {},
        "missing_components": [],
        "required_actions": []
    }
    
    # 1. Check AWS Credentials
    print("1. AWS Credentials & Access")
    try:
        sts = session.client('sts')
        identity = sts.get_caller_identity()
        print(f"   ✅ Account: {identity['Account']}")
        print(f"   ✅ Region: {session.region_name}")
        status_report["aws_services"]["credentials"] = "CONNECTED"
    except Exception as e:
        print(f"   ❌ Credentials failed: {e}")
        status_report["aws_services"]["credentials"] = "FAILED"
        return status_report
    
    # 2. Check Bedrock Access
    print("2. Amazon Bedrock Service")
    try:
        bedrock = session.client('bedrock')
        models = bedrock.list_foundation_models()
        claude_models = [m for m in models['modelSummaries'] if 'claude' in m['modelId'].lower()]
        
        if claude_models:
            print(f"   ✅ Bedrock access: {len(claude_models)} Claude models available")
            status_report["aws_services"]["bedrock"] = "CONNECTED"
        else:
            print("   ⚠️ Bedrock access but no Claude models found")
            status_report["aws_services"]["bedrock"] = "LIMITED"
    except Exception as e:
        print(f"   ❌ Bedrock access failed: {e}")
        status_report["aws_services"]["bedrock"] = "FAILED"
        status_report["missing_components"].append("Bedrock service access")
    
    # 3. Check Bedrock Agents
    print("3. Bedrock Agents")
    try:
        bedrock_agent = session.client('bedrock-agent')
        agents = bedrock_agent.list_agents()
        
        required_agents = [
            "threat-classifier",
            "investigation-agent", 
            "response-orchestration",
            "threat-intelligence",
            "root-cause-analysis"
        ]
        
        found_agents = []
        for agent in agents.get('agentSummaries', []):
            agent_name = agent['agentName'].lower()
            for req_agent in required_agents:
                if req_agent in agent_name:
                    found_agents.append(req_agent)
                    print(f"   ✅ {req_agent}: {agent['agentStatus']}")
        
        missing_agents = set(required_agents) - set(found_agents)
        for missing in missing_agents:
            print(f"   ❌ {missing}: NOT DEPLOYED")
            status_report["missing_components"].append(f"Bedrock Agent: {missing}")
        
        status_report["bedrock_agents"]["deployed"] = len(found_agents)
        status_report["bedrock_agents"]["required"] = len(required_agents)
        
    except Exception as e:
        print(f"   ❌ Bedrock Agents check failed: {e}")
        status_report["bedrock_agents"]["status"] = "FAILED"
        status_report["missing_components"].extend([
            "All 5 Bedrock Agents need deployment"
        ])
    
    # 4. Check Kinesis Streams
    print("4. Kinesis Data Streams")
    try:
        kinesis = session.client('kinesis')
        streams = kinesis.list_streams()
        
        required_streams = ["vpc-flow-logs-stream"]
        found_streams = []
        
        for stream in streams['StreamNames']:
            if any(req in stream for req in required_streams):
                found_streams.append(stream)
                # Check stream status
                desc = kinesis.describe_stream(StreamName=stream)
                status = desc['StreamDescription']['StreamStatus']
                print(f"   ✅ {stream}: {status}")
        
        missing_streams = set(required_streams) - set(found_streams)
        for missing in missing_streams:
            print(f"   ❌ {missing}: NOT FOUND")
            status_report["missing_components"].append(f"Kinesis Stream: {missing}")
        
        status_report["infrastructure"]["kinesis"] = "PARTIAL" if found_streams else "MISSING"
        
    except Exception as e:
        print(f"   ❌ Kinesis check failed: {e}")
        status_report["infrastructure"]["kinesis"] = "FAILED"
    
    # 5. Check DynamoDB Tables
    print("5. DynamoDB Tables")
    try:
        dynamodb = session.client('dynamodb')
        tables = dynamodb.list_tables()
        
        required_tables = [
            "threat-incidents",
            "threat-intel", 
            "analyst-feedback"
        ]
        
        found_tables = []
        for table in tables['TableNames']:
            if any(req in table for req in required_tables):
                found_tables.append(table)
                # Check table status
                desc = dynamodb.describe_table(TableName=table)
                status = desc['Table']['TableStatus']
                print(f"   ✅ {table}: {status}")
        
        missing_tables = set(required_tables) - set(found_tables)
        for missing in missing_tables:
            print(f"   ❌ {missing}: NOT FOUND")
            status_report["missing_components"].append(f"DynamoDB Table: {missing}")
        
        status_report["infrastructure"]["dynamodb"] = "PARTIAL" if found_tables else "MISSING"
        
    except Exception as e:
        print(f"   ❌ DynamoDB check failed: {e}")
        status_report["infrastructure"]["dynamodb"] = "FAILED"
    
    # 6. Check Lambda Functions
    print("6. Lambda Functions")
    try:
        lambda_client = session.client('lambda')
        functions = lambda_client.list_functions()
        
        required_functions = [
            "vpc-threat-detector",
            "threat-enrichment",
            "agent-orchestrator"
        ]
        
        found_functions = []
        for func in functions['Functions']:
            func_name = func['FunctionName']
            if any(req in func_name for req in required_functions):
                found_functions.append(func_name)
                print(f"   ✅ {func_name}: {func['State']}")
        
        missing_functions = set(required_functions) - set(found_functions)
        for missing in missing_functions:
            print(f"   ❌ {missing}: NOT FOUND")
            status_report["missing_components"].append(f"Lambda Function: {missing}")
        
        status_report["infrastructure"]["lambda"] = "PARTIAL" if found_functions else "MISSING"
        
    except Exception as e:
        print(f"   ❌ Lambda check failed: {e}")
        status_report["infrastructure"]["lambda"] = "FAILED"
    
    # 7. Check SageMaker
    print("7. SageMaker ML Models")
    try:
        sagemaker = session.client('sagemaker')
        endpoints = sagemaker.list_endpoints()
        
        required_models = ["isolation-forest", "lstm-behavioral"]
        found_models = []
        
        for endpoint in endpoints['Endpoints']:
            endpoint_name = endpoint['EndpointName']
            if any(req in endpoint_name for req in required_models):
                found_models.append(endpoint_name)
                print(f"   ✅ {endpoint_name}: {endpoint['EndpointStatus']}")
        
        if not found_models:
            print("   ❌ No ML model endpoints found")
            status_report["missing_components"].extend([
                "SageMaker Isolation Forest Model",
                "SageMaker LSTM Behavioral Model"
            ])
        
        status_report["infrastructure"]["sagemaker"] = "DEPLOYED" if found_models else "MISSING"
        
    except Exception as e:
        print(f"   ❌ SageMaker check failed: {e}")
        status_report["infrastructure"]["sagemaker"] = "FAILED"
    
    # 8. Check Step Functions
    print("8. Step Functions Workflows")
    try:
        stepfunctions = session.client('stepfunctions')
        state_machines = stepfunctions.list_state_machines()
        
        threat_workflows = []
        for sm in state_machines['stateMachines']:
            if 'threat' in sm['name'].lower() or 'vpc' in sm['name'].lower():
                threat_workflows.append(sm['name'])
                print(f"   ✅ {sm['name']}: {sm['status']}")
        
        if not threat_workflows:
            print("   ❌ No threat detection workflows found")
            status_report["missing_components"].append("Step Functions Threat Detection Workflow")
        
        status_report["infrastructure"]["step_functions"] = "DEPLOYED" if threat_workflows else "MISSING"
        
    except Exception as e:
        print(f"   ❌ Step Functions check failed: {e}")
        status_report["infrastructure"]["step_functions"] = "FAILED"
    
    # 9. Check OpenSearch
    print("9. OpenSearch Service")
    try:
        opensearch = session.client('opensearch')
        domains = opensearch.list_domain_names()
        
        vpc_domains = []
        for domain in domains['DomainNames']:
            if 'vpc' in domain['DomainName'].lower() or 'flow' in domain['DomainName'].lower():
                vpc_domains.append(domain['DomainName'])
                # Get domain status
                desc = opensearch.describe_domain(DomainName=domain['DomainName'])
                status = desc['DomainStatus']['Processing']
                print(f"   ✅ {domain['DomainName']}: {'Processing' if status else 'Active'}")
        
        if not vpc_domains:
            print("   ❌ No OpenSearch domains found")
            status_report["missing_components"].append("OpenSearch Domain for flow logs")
        
        status_report["infrastructure"]["opensearch"] = "DEPLOYED" if vpc_domains else "MISSING"
        
    except Exception as e:
        print(f"   ❌ OpenSearch check failed: {e}")
        status_report["infrastructure"]["opensearch"] = "FAILED"
    
    # 10. Generate Summary and Recommendations
    print("\n" + "="*60)
    print("SYSTEM STATUS SUMMARY")
    print("="*60)
    
    total_missing = len(status_report["missing_components"])
    if total_missing == 0:
        print("🎉 SYSTEM FULLY DEPLOYED - All components operational!")
    else:
        print(f"⚠️ PARTIAL DEPLOYMENT - {total_missing} components missing")
    
    print(f"\nAWS Services Status:")
    for service, status in status_report["aws_services"].items():
        emoji = "✅" if status == "CONNECTED" else "❌"
        print(f"  {emoji} {service}: {status}")
    
    print(f"\nInfrastructure Status:")
    for component, status in status_report["infrastructure"].items():
        emoji = "✅" if status == "DEPLOYED" else "⚠️" if status == "PARTIAL" else "❌"
        print(f"  {emoji} {component}: {status}")
    
    if status_report["missing_components"]:
        print(f"\nMissing Components ({len(status_report['missing_components'])}):")
        for i, component in enumerate(status_report["missing_components"], 1):
            print(f"  {i}. {component}")
    
    # Generate action plan
    print(f"\nRECOMMENDED ACTIONS:")
    
    if status_report["aws_services"].get("bedrock") == "FAILED":
        print("  1. Enable Amazon Bedrock service in AWS Console")
        print("     - Go to Bedrock console and request model access")
        print("     - Enable Claude 3.5 Sonnet and Haiku models")
    
    if status_report["bedrock_agents"].get("deployed", 0) < 5:
        print("  2. Deploy Bedrock Agents")
        print("     - Run: cd deployment && python deploy-bedrock-agents.py")
    
    if status_report["infrastructure"].get("kinesis") == "MISSING":
        print("  3. Deploy Core Infrastructure")
        print("     - Run: python quick-deploy.py (for basic setup)")
        print("     - Run: python deploy.py (for full deployment)")
    
    if total_missing > 5:
        print("  4. Full System Deployment Required")
        print("     - Run: cd deployment && python deploy.py")
        print("     - This will deploy all missing components")
    
    print(f"\nNext Steps:")
    print("  • Fix missing components above")
    print("  • Run: python test-credentials.py (verify access)")
    print("  • Run: python quick-test.py (test basic functionality)")
    print("  • Run: python load-test.py (performance validation)")
    
    return status_report

if __name__ == "__main__":
    status = check_system_status()
    
    # Save status report
    with open('system-status-report.json', 'w') as f:
        json.dump(status, f, indent=2)
    
    print(f"\n📄 Detailed report saved to: system-status-report.json")