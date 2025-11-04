#!/usr/bin/env python3
import boto3
import os

# Test credentials
try:
    session = boto3.Session(
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        aws_session_token=os.getenv('AWS_SESSION_TOKEN'),
        region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    )
    
    sts = session.client('sts')
    identity = sts.get_caller_identity()
    print(f"SUCCESS: Account {identity['Account']}")
    
except Exception as e:
    print(f"FAILED: {e}")