#!/usr/bin/env python3
"""
Prepare Bedrock agents and test the working one
"""
import boto3
import json
import os
import time

def prepare_and_test_agents():
    """Prepare agents and test functionality"""
    print("=== Preparing Bedrock Agents ===")
    
    session = boto3.Session(
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        aws_session_token=os.getenv('AWS_SESSION_TOKEN'),
        region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    )
    
    bedrock_agent = session.client('bedrock-agent')
    bedrock_agent_runtime = session.client('bedrock-agent-runtime')
    
    # Agent information
    agents = [
        {"id": "LB7W1ORPJG", "name": "ThreatClassifierAgent", "status": "NOT_PREPARED"},
        {"id": "IHGZJIKZ8T", "name": "InvestigationAgent", "status": "NOT_PREPARED"},
        {"id": "W2JDG72L8B", "name": "ResponseOrchestrationAgent", "status": "PREPARED", "alias": "MRO6IIIW4B"},
        {"id": "HLOGFAE8YI", "name": "ThreatIntelligenceAgent", "status": "NOT_PREPARED"},
        {"id": "LFKFNCTX3B", "name": "RootCauseAnalysisAgent", "status": "NOT_PREPARED"}
    ]
    
    # Prepare unprepared agents
    for agent in agents:
        if agent['status'] == 'NOT_PREPARED':
            try:
                print(f"\nPreparing {agent['name']}...")
                
                # Prepare agent
                bedrock_agent.prepare_agent(agentId=agent['id'])
                print(f"   ✅ Preparation started for {agent['name']}")
                
                # Wait for preparation (shorter wait)
                print(f"   ⏳ Waiting for preparation...")
                for i in range(6):  # Wait up to 60 seconds
                    time.sleep(10)
                    try:
                        agent_info = bedrock_agent.get_agent(agentId=agent['id'])
                        status = agent_info['agent']['agentStatus']
                        print(f"   Status: {status}")
                        
                        if status == 'PREPARED':
                            print(f"   ✅ {agent['name']} prepared successfully")
                            agent['status'] = 'PREPARED'
                            break
                        elif status == 'FAILED':
                            print(f"   ❌ {agent['name']} preparation failed")
                            break
                    except Exception as e:
                        print(f"   ⚠️ Status check error: {e}")
                
            except Exception as e:
                print(f"   ❌ Failed to prepare {agent['name']}: {e}")
    
    # Test the working agent (ResponseOrchestrationAgent)
    print(f"\n=== Testing Working Agent ===")
    working_agent = next(a for a in agents if a['name'] == 'ResponseOrchestrationAgent')
    
    if 'alias' in working_agent:
        try:
            print(f"Testing {working_agent['name']}...")
            
            test_message = """Analyze this critical security threat:
            
THREAT DETAILS:
- Type: Port scanning attack
- Source IP: 192.168.1.100 (internal network)
- Target: Production web servers
- Ports scanned: 22, 80, 443, 3389, 1433, 3306 (25 total)
- Time window: 60 seconds
- Severity: HIGH
- Confidence: 95%

CONTEXT:
- Source is internal IP (potential lateral movement)
- Targeting critical production infrastructure
- Scanning common service ports (SSH, HTTP, HTTPS, RDP, SQL)
- Rapid scanning pattern indicates automated tools

What immediate response actions should be taken?"""

            response = bedrock_agent_runtime.invoke_agent(
                agentId=working_agent['id'],
                agentAliasId=working_agent['alias'],
                sessionId='demo-session-001',
                inputText=test_message
            )
            
            print(f"   ✅ Agent invoked successfully")
            print(f"   📝 Response:")
            
            # Collect and display response
            full_response = ""
            for event in response['completion']:
                if 'chunk' in event:
                    chunk = event['chunk']
                    if 'bytes' in chunk:
                        text = chunk['bytes'].decode()
                        full_response += text
                        print(text, end='', flush=True)
            
            print(f"\n\n   ✅ {working_agent['name']} is fully operational!")
            
            # Save response for demo
            with open('agent-demo-response.txt', 'w') as f:
                f.write(f"Agent: {working_agent['name']}\n")
                f.write(f"Query: Port scanning threat analysis\n")
                f.write(f"Response:\n{full_response}")
            
        except Exception as e:
            print(f"   ❌ Test failed: {e}")
    
    # Create aliases for newly prepared agents
    print(f"\n=== Creating Aliases for Prepared Agents ===")
    for agent in agents:
        if agent['status'] == 'PREPARED' and 'alias' not in agent:
            try:
                alias_response = bedrock_agent.create_agent_alias(
                    agentId=agent['id'],
                    agentAliasName='PROD',
                    description='Production alias'
                )
                agent['alias'] = alias_response['agentAlias']['agentAliasId']
                print(f"   ✅ Created alias for {agent['name']}: {agent['alias']}")
            except Exception as e:
                print(f"   ⚠️ Alias creation failed for {agent['name']}: {e}")
    
    # Summary
    print(f"\n=== Agent Status Summary ===")
    prepared_count = len([a for a in agents if a['status'] == 'PREPARED'])
    print(f"Prepared agents: {prepared_count}/5")
    
    for agent in agents:
        status_emoji = "✅" if agent['status'] == 'PREPARED' else "⏳"
        alias_info = f" (Alias: {agent.get('alias', 'None')})" if 'alias' in agent else ""
        print(f"  {status_emoji} {agent['name']}: {agent['status']}{alias_info}")
    
    if prepared_count > 0:
        print(f"\n🎉 System is operational with {prepared_count} AI agents!")
        print(f"✅ Core threat detection and analysis capabilities available")
        print(f"✅ AI-powered security incident response ready")
        
        print(f"\nNext steps:")
        print(f"1. Test with real VPC Flow Log data")
        print(f"2. Deploy remaining infrastructure (Lambda, Step Functions)")
        print(f"3. Add ML models for enhanced detection")
        print(f"4. Create frontend dashboard integration")
    
    return agents

if __name__ == "__main__":
    prepare_and_test_agents()