import os
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from flask import request
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# AWS Configuration
AWS_REGION = os.getenv("AWS_REGION")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

def verify_aws_signature(req):
    """ Fully Verify AWS Signature Version 4 (SigV4) """
    auth_header = req.headers.get("Authorization", "")
    if not auth_header:
        return False, "Missing Authorization header"

    # Extract AWS Access Key from Authorization header
    try:
        credentials_part = auth_header.split("Credential=")[1].split(",")[0]
        aws_access_key = credentials_part.split("/")[0]
    except IndexError:
        return False, "Invalid Authorization header format"

    # Validate if the provided access key matches the one in `.env`
    if aws_access_key != AWS_ACCESS_KEY_ID:
        return False, "Unauthorized AWS Access Key"

    # Initialize AWS credentials manually
    session = boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        aws_session_token=AWS_SESSION_TOKEN
    )
    credentials = session.get_credentials()

    # Create a request object for verification
    request_to_validate = AWSRequest(
        method=req.method, url=req.url, headers=dict(req.headers), data=req.get_data()
    )
    
    # Recreate the signature using the secret key
    SigV4Auth(credentials, "execute-api", AWS_REGION).add_auth(request_to_validate)

    # Compare the expected vs received signature
    expected_signature = request_to_validate.headers.get("Authorization")
    if expected_signature != auth_header:
        return False, "Invalid Signature"

    return True, "Signature Valid"
