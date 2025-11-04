#!/usr/bin/env python3
"""
Deploy Amazon Bedrock Agents for VPC Flow Log Anomaly Detection System
Creates all 5 specialized AI agents with proper configurations
"""
import boto3
import json
import os
import time
from datetime import datetime

def deploy_bedrock_agents():
    """Deploy all Bedrock agents for threat detection"""
    print("=== Deploying Bedrock Agents ===")
    
    session = boto3.Session(
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        aws_session_token=os.getenv('AWS_SESSION_TOKEN'),
        region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    )
    
    bedrock_agent = session.client('bedrock-agent')
    iam = session.client('iam')
    
    # Create IAM role for agents
    agent_role_arn = create_agent_execution_role(iam)
    
    agents_config = [
        {
            "name": "ThreatClassifierAgent",
            "description": "Analyzes network anomalies and classifies threats with severity and confidence scores",
            "model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
            "instruction": """You are a cybersecurity expert specializing in network threat analysis. 

Analyze network anomalies and determine:
- is_threat (boolean): Whether this represents a genuine security threat
- severity (CRITICAL/HIGH/MEDIUM/LOW): Risk level based on potential impact
- confidence (0-100): Your confidence in the assessment
- threat_type: Specific category (port_scanning, crypto_mining, lateral_movement, etc.)
- mitre_attack_techniques: Relevant MITRE ATT&CK technique IDs
- reasoning: Detailed explanation of your analysis
- recommended_actions: Specific steps to address the threat

Consider context like:
- Resource type and normal behavior patterns
- Business justification for the activity
- Potential false positive scenarios
- Blast radius and potential impact
- Historical patterns and baselines

Provide clear, actionable analysis with specific evidence.""",
            "tools": [
                {
                    "name": "get_resource_baseline",
                    "description": "Get normal behavior baseline for a resource"
                },
                {
                    "name": "check_threat_intel", 
                    "description": "Check IP/domain against threat intelligence feeds"
                },
                {
                    "name": "get_recent_cloudtrail",
                    "description": "Get recent CloudTrail API activity for context"
                }
            ]
        },
        {
            "name": "InvestigationAgent",
            "description": "Conducts deep investigation of confirmed threats using multiple data sources",
            "model": "anthropic.claude-3-5-sonnet-20241022-v2:0", 
            "instruction": """You are a senior incident response analyst conducting thorough security investigations.

For confirmed threats, build comprehensive analysis including:
- Attack timeline with specific timestamps and events
- Entry vector identification and initial compromise method
- Lateral movement mapping across network segments
- Data access assessment and potential exfiltration
- Persistence mechanism identification
- Evidence collection from multiple sources

Use available tools strategically to gather evidence:
- Query CloudTrail for API activity patterns
- Analyze historical network flows for movement patterns
- Check IAM permissions for privilege escalation
- Correlate with vulnerability data and threat intelligence
- Map network topology for lateral movement paths

Provide detailed findings with:
- Executive summary of the incident
- Technical timeline with evidence
- Impact assessment and affected systems
- Containment and remediation recommendations
- Lessons learned and prevention measures""",
            "tools": [
                {
                    "name": "query_cloudtrail",
                    "description": "Query CloudTrail logs for API activity analysis"
                },
                {
                    "name": "query_flow_logs_history", 
                    "description": "Query historical VPC flow logs in OpenSearch"
                },
                {
                    "name": "get_iam_permissions",
                    "description": "Analyze IAM permissions for privilege escalation"
                },
                {
                    "name": "check_vulnerabilities",
                    "description": "Check for known vulnerabilities on resources"
                },
                {
                    "name": "query_guardduty",
                    "description": "Query GuardDuty for correlated findings"
                },
                {
                    "name": "get_network_topology",
                    "description": "Get VPC network topology for lateral movement analysis"
                }
            ]
        },
        {
            "name": "ResponseOrchestrationAgent",
            "description": "Executes automated incident response based on threat severity",
            "model": "anthropic.claude-3-5-haiku-20241022:0",
            "instruction": """You are an incident response coordinator executing containment actions.

Based on threat severity, execute appropriate response:

CRITICAL threats:
- Immediate isolation of affected resources
- Credential revocation for compromised accounts
- Alert security team via PagerDuty
- Create high-priority incident ticket
- Prepare forensic snapshots

HIGH threats:
- Prepare isolation (don't execute without approval)
- Create forensic snapshots
- Alert security team via Slack
- Create incident ticket
- Gather additional evidence

MEDIUM/LOW threats:
- Log for analyst review
- Create informational ticket
- Schedule follow-up analysis

Always:
- Request human approval for destructive actions in production
- Provide clear justification for each action
- Estimate execution time and impact
- Offer rollback procedures where applicable
- Document all actions taken""",
            "tools": [
                {
                    "name": "isolate_instance",
                    "description": "Isolate EC2 instance by modifying security groups"
                },
                {
                    "name": "snapshot_for_forensics",
                    "description": "Create EBS snapshot for forensic analysis"
                },
                {
                    "name": "revoke_credentials",
                    "description": "Revoke IAM credentials and sessions"
                },
                {
                    "name": "block_ip_at_waf",
                    "description": "Add IP to WAF block list"
                },
                {
                    "name": "notify_team",
                    "description": "Send notifications via Slack/PagerDuty/SNS"
                },
                {
                    "name": "create_incident_ticket",
                    "description": "Create incident ticket in JIRA/ServiceNow"
                }
            ]
        },
        {
            "name": "ThreatIntelligenceAgent",
            "description": "Enriches threats with external intelligence and historical context",
            "model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
            "instruction": """You are a threat intelligence analyst providing context and enrichment.

Enrich threat data with:
- External threat intelligence from multiple feeds
- Historical incident correlation and patterns
- MITRE ATT&CK technique mapping
- Threat actor attribution when possible
- Campaign and malware family identification
- Geolocation and infrastructure analysis

Provide intelligence assessment including:
- Threat actor profiles and capabilities
- Campaign context and objectives
- Infrastructure relationships and patterns
- Recommended defensive measures
- IOCs for detection and blocking
- Similar historical incidents and outcomes

Use knowledge base to:
- Query MITRE ATT&CK framework
- Search historical incident database
- Correlate with known threat campaigns
- Provide response playbooks and procedures""",
            "tools": [
                {
                    "name": "query_threat_feeds",
                    "description": "Query external threat intelligence feeds"
                },
                {
                    "name": "search_mitre_attack",
                    "description": "Search MITRE ATT&CK knowledge base"
                },
                {
                    "name": "correlate_historical_incidents",
                    "description": "Find similar historical incidents"
                },
                {
                    "name": "analyze_infrastructure",
                    "description": "Analyze threat infrastructure and relationships"
                }
            ]
        },
        {
            "name": "RootCauseAnalysisAgent", 
            "description": "Conducts post-incident analysis to prevent future occurrences",
            "model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
            "instruction": """You are a security architect conducting root cause analysis.

Analyze resolved incidents to identify:
- Root cause of the security failure
- Contributing factors and systemic issues
- Control failures and gaps in defense
- Detection timing and effectiveness
- Response effectiveness and delays

Provide actionable recommendations:
- Specific preventive measures with implementation details
- Detection improvements and new monitoring rules
- Process improvements and training needs
- Technology upgrades and security controls
- Effort estimates and priority rankings

Review security posture including:
- Security group configurations and network segmentation
- IAM policies and privilege management
- Patch management and vulnerability handling
- Monitoring coverage and alert tuning
- Incident response procedures and automation

Focus on systemic improvements rather than just fixing the immediate issue.""",
            "tools": [
                {
                    "name": "analyze_security_groups",
                    "description": "Analyze security group configurations for gaps"
                },
                {
                    "name": "review_iam_policies", 
                    "description": "Review IAM policies for excessive permissions"
                },
                {
                    "name": "check_patch_status",
                    "description": "Check patch status across infrastructure"
                },
                {
                    "name": "analyze_monitoring_gaps",
                    "description": "Identify monitoring and detection gaps"
                }
            ]
        }
    ]
    
    deployed_agents = []
    
    for agent_config in agents_config:
        try:
            print(f"\nDeploying {agent_config['name']}...")
            
            # Create agent
            response = bedrock_agent.create_agent(
                agentName=agent_config['name'],
                description=agent_config['description'],
                foundationModel=agent_config['model'],
                instruction=agent_config['instruction'],
                agentResourceRoleArn=agent_role_arn,
                idleSessionTTLInSeconds=1800  # 30 minutes
            )
            
            agent_id = response['agent']['agentId']
            print(f"   ✅ Agent created: {agent_id}")
            
            # Create action group for tools
            if agent_config['tools']:
                action_group_response = bedrock_agent.create_agent_action_group(
                    agentId=agent_id,
                    agentVersion='DRAFT',
                    actionGroupName=f"{agent_config['name']}Tools",
                    description=f"Tools for {agent_config['name']}",
                    actionGroupExecutor={
                        'lambda': f"arn:aws:lambda:{session.region_name}:{session.client('sts').get_caller_identity()['Account']}:function:bedrock-agent-tools"
                    },
                    apiSchema={
                        'payload': json.dumps({
                            "openapi": "3.0.0",
                            "info": {"title": f"{agent_config['name']} Tools", "version": "1.0.0"},
                            "paths": {f"/{tool['name']}": {
                                "post": {
                                    "description": tool['description'],
                                    "responses": {"200": {"description": "Success"}}
                                }
                            } for tool in agent_config['tools']}
                        })
                    }
                )
                print(f"   ✅ Action group created")
            
            # Prepare agent
            prepare_response = bedrock_agent.prepare_agent(
                agentId=agent_id
            )
            print(f"   ✅ Agent prepared")
            
            # Create alias
            alias_response = bedrock_agent.create_agent_alias(
                agentId=agent_id,
                agentAliasName='PROD',
                description='Production alias'
            )
            
            deployed_agents.append({
                'name': agent_config['name'],
                'agent_id': agent_id,
                'alias_id': alias_response['agentAlias']['agentAliasId'],
                'status': 'DEPLOYED'
            })
            
            print(f"   ✅ {agent_config['name']} deployed successfully")
            
        except Exception as e:
            print(f"   ❌ Failed to deploy {agent_config['name']}: {e}")
            deployed_agents.append({
                'name': agent_config['name'],
                'status': 'FAILED',
                'error': str(e)
            })
    
    # Save agent configuration
    with open('deployed-agents.json', 'w') as f:
        json.dump(deployed_agents, f, indent=2)
    
    print(f"\n=== Deployment Summary ===")
    successful = len([a for a in deployed_agents if a['status'] == 'DEPLOYED'])
    print(f"Successfully deployed: {successful}/5 agents")
    
    if successful == 5:
        print("🎉 All Bedrock agents deployed successfully!")
        print("Next steps:")
        print("  1. Deploy Lambda function for agent tools")
        print("  2. Test agent responses: python test-agents.py")
        print("  3. Deploy remaining infrastructure")
    else:
        print("⚠️ Some agents failed to deploy. Check errors above.")
    
    return deployed_agents

def create_agent_execution_role(iam_client):
    """Create IAM role for Bedrock agent execution"""
    role_name = "BedrockAgentExecutionRole"
    
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "bedrock.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    try:
        # Create role
        response = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="Execution role for Bedrock agents in VPC anomaly detection system"
        )
        
        # Attach policies
        policies = [
            "arn:aws:iam::aws:policy/AmazonBedrockFullAccess",
            "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
        ]
        
        for policy in policies:
            iam_client.attach_role_policy(
                RoleName=role_name,
                PolicyArn=policy
            )
        
        print(f"✅ Created IAM role: {role_name}")
        return response['Role']['Arn']
        
    except iam_client.exceptions.EntityAlreadyExistsException:
        # Role already exists, get ARN
        response = iam_client.get_role(RoleName=role_name)
        print(f"✅ Using existing IAM role: {role_name}")
        return response['Role']['Arn']

if __name__ == "__main__":
    deploy_bedrock_agents()