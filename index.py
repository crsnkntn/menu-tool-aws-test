import json
import boto3
import os
from generate_menu_handler import GenerateMenuHandler

def handler(event, context):
    """Triggered by SQS to process menu generation requests."""
    for record in event["Records"]:
        message_body = json.loads(record["body"])
        url = message_body["url"]
        request_id = message_body["requestId"]

        try:
            gen_handler = GenerateMenuHandler(url, request_id)
            gen_handler.run()
        except Exception as e:
            print(f"Error processing request {request_id}: {str(e)}")
