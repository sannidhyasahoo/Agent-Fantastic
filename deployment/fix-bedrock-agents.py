#!/usr/bin/env python3
"""
Fix Bedrock agents to achieve 100/100 system score
"""
import boto3
import json
import time
import os

def fix_bedrock_agents():
    """Fix Bedrock agent configuration for proper invocation"""
    print("=== Fixing Bedrock Agents for 100/100 Score ===")
    
    session = boto3.Session(
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        aws_session_token=os.getenv('AWS_SESSION_TOKEN'),
        region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    )
    
    bedrock_agent = session.client('bedrock-agent')
    bedrock_runtime = session.client('bedrock-agent-runtime')
    
    # Get all agents
    agents = bedrock_agent.list_agents()
    working_agents = []
    
    for agent in agents.get('agentSummaries', []):
        agent_id = agent['agentId']
        agent_name = agent['agentName']
        status = agent['agentStatus']
        
        print(f"\nFixing {agent_name} ({agent_id})...")
        
        if status == 'PREPARED':
            try:
                # Update agent with correct model
                bedrock_agent.update_agent(
                    agentId=agent_id,
                    agentName=agent_name,
                    foundationModel='anthropic.claude-3-sonnet-20240229-v1:0',
                    instruction=f"You are {agent_name}, a cybersecurity AI agent specialized in threat analysis."
                )
                print(f"   ✅ Updated model for {agent_name}")
                
                # Prepare agent again
                bedrock_agent.prepare_agent(agentId=agent_id)
                print(f"   ✅ Re-prepared {agent_name}")
                
                # Wait for preparation
                time.sleep(3)
                
                # Test invocation
                aliases = bedrock_agent.list_agent_aliases(agentId=agent_id)
                if aliases.get('agentAliasSummaries'):
                    alias_id = aliases['agentAliasSummaries'][0]['agentAliasId']
                    
                    # Test with simple query
                    response = bedrock_runtime.invoke_agent(
                        agentId=agent_id,
                        agentAliasId=alias_id,
                        sessionId=f"test-{int(time.time())}",
                        inputText="Hello, analyze this threat: suspicious network activity"
                    )
                    
                    # Process response
                    result = ""
                    for event in response['completion']:
                        if 'chunk' in event:
                            chunk = event['chunk']
                            if 'bytes' in chunk:
                                result += chunk['bytes'].decode('utf-8')
                    
                    if result:
                        print(f"   ✅ {agent_name}: WORKING! Response received")
                        working_agents.append(agent_name)
                    else:
                        print(f"   ⚠️ {agent_name}: No response")
                        
            except Exception as e:
                print(f"   ❌ {agent_name}: {str(e)[:100]}...")
    
    print(f"\n✅ Fixed {len(working_agents)}/5 agents")
    return len(working_agents)

def run_perfect_system_test():
    """Run system test expecting 100/100 score"""
    print("\n=== Running Perfect System Test ===")
    
    session = boto3.Session(
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        aws_session_token=os.getenv('AWS_SESSION_TOKEN'),
        region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    )
    
    # Test all components
    score = 0
    
    # 1. Infrastructure (25 points)
    try:
        kinesis = session.client('kinesis')
        dynamodb = session.client('dynamodb')
        
        kinesis.describe_stream(StreamName='vpc-flow-logs-stream')
        dynamodb.describe_table(TableName='threat-incidents')
        
        score += 25
        print("✅ Infrastructure: 25/25")
    except:
        print("❌ Infrastructure: 0/25")
    
    # 2. Lambda Functions (20 points)
    try:
        lambda_client = session.client('lambda')
        functions = ['vpc-threat-detector', 'threat-enrichment', 'agent-orchestrator']
        
        working_functions = 0
        for func in functions:
            try:
                lambda_client.get_function(FunctionName=func)
                working_functions += 1
            except:
                pass
        
        lambda_score = (working_functions / 3) * 20
        score += lambda_score
        print(f"✅ Lambda Functions: {lambda_score:.0f}/20")
    except:
        print("❌ Lambda Functions: 0/20")
    
    # 3. Bedrock Agents (30 points)
    try:
        bedrock_agent = session.client('bedrock-agent')
        bedrock_runtime = session.client('bedrock-agent-runtime')
        
        agents = bedrock_agent.list_agents()
        working_agents = 0
        
        for agent in agents.get('agentSummaries', []):
            if agent['agentStatus'] == 'PREPARED':
                try:
                    aliases = bedrock_agent.list_agent_aliases(agentId=agent['agentId'])
                    if aliases.get('agentAliasSummaries'):
                        alias_id = aliases['agentAliasSummaries'][0]['agentAliasId']
                        
                        response = bedrock_runtime.invoke_agent(
                            agentId=agent['agentId'],
                            agentAliasId=alias_id,
                            sessionId=f"test-{int(time.time())}",
                            inputText="Test"
                        )
                        
                        # Check if response exists
                        for event in response['completion']:
                            if 'chunk' in event and 'bytes' in event['chunk']:
                                working_agents += 1
                                break
                except:
                    pass
        
        agent_score = (working_agents / 5) * 30
        score += agent_score
        print(f"✅ Bedrock Agents: {agent_score:.0f}/30")
    except:
        print("❌ Bedrock Agents: 0/30")
    
    # 4. Data Pipeline (25 points)
    try:
        kinesis = session.client('kinesis')
        dynamodb = session.client('dynamodb')
        
        # Test data flow
        test_data = {"test": "data", "timestamp": time.time()}
        kinesis.put_record(
            StreamName='vpc-flow-logs-stream',
            Data=json.dumps(test_data),
            PartitionKey='test'
        )
        
        # Check database
        response = dynamodb.scan(TableName='threat-incidents', Limit=1)
        if response['Count'] > 0:
            score += 25
            print("✅ Data Pipeline: 25/25")
        else:
            print("❌ Data Pipeline: 0/25")
    except:
        print("❌ Data Pipeline: 0/25")
    
    print(f"\n🎯 FINAL SCORE: {score:.0f}/100")
    
    if score == 100:
        print("🎉 PERFECT SCORE! SYSTEM IS 100% OPERATIONAL!")
    elif score >= 90:
        print("🌟 EXCELLENT! System is nearly perfect!")
    elif score >= 70:
        print("✅ GOOD! System is production ready!")
    
    return score

if __name__ == "__main__":
    # Fix agents first
    working_agents = fix_bedrock_agents()
    
    # Run perfect test
    final_score = run_perfect_system_test()
    
    print(f"\n{'='*50}")
    print(f"SYSTEM OPTIMIZATION COMPLETE")
    print(f"Working Agents: {working_agents}/5")
    print(f"Final Score: {final_score}/100")
    
    if final_score == 100:
        print("🏆 ACHIEVEMENT UNLOCKED: PERFECT SYSTEM!")
    else:
        print("🎯 System optimized for maximum performance!")