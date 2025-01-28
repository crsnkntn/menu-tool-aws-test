import json
import time
import boto3
from botocore.exceptions import ClientError

# AWS S3 bucket setup
S3_BUCKET = "menu-tool-bucket"
s3_client = boto3.client("s3")

all_states = [
    "Crawling & Scraping the Page ...",
    "Cleaning the Scraped Content ...",
    "Generating the Menu Item Templates ...",
    "Expanding the Menu Item Templates ...",
    "Cleaning and Refining all Menu Items ..."
]


def handler(event, context):
    try:
        # Parse the HTTP method and path
        body = json.loads(event.get("body", "{}"))

        request_type = body.get("requestType", "")

        if request_type == "gen":
            return handle_generate_request(body)
        elif request_type == "get-status":
            return handle_generation_status(body)

        return {
            "statusCode": 404,
            "body": json.dumps({"message": f"Error: Request type \"{request_type}\" does not exist."}),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Internal Server Error", "error": str(e)}),
        }


def save_request_to_s3(request_id, data):
    """Save a request object to S3."""
    try:
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=f"requests/{request_id}.json",
            Body=json.dumps(data),
            ContentType="application/json",
        )
    except ClientError as e:
        raise Exception(f"Error saving to S3: {e}")


def get_request_from_s3(request_id):
    """Retrieve a request object from S3."""
    try:
        response = s3_client.get_object(
            Bucket=S3_BUCKET,
            Key=f"requests/{request_id}.json"
        )
        return json.loads(response["Body"].read())
    except ClientError as e:
        raise Exception(f"Error fetching from S3: {e}")


def handle_generate_request(body):
    """Handles the initial request to generate a menu."""
    try:
        url = body.get("url", "")

        if not url:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "URL is required"}),
            }

        # Generate a unique request ID
        request_id = f"request_{int(time.time())}"

        # Create the initial status object
        request_data = {
            "status": "GENERATING",
            "message": all_states[0],
            "menuItems": None,
        }

        # Save to S3
        save_request_to_s3(request_id, request_data)

        return {
            "statusCode": 200,
            "body": json.dumps({"requestId": request_id}),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Failed to initiate menu generation", "error": str(e)}),
        }


def handle_generation_status(body):
    """Handles polling for the generation status."""
    try:
        request_id = body.get("requestId", "")
        is_canceled = body.get("isCanceled", False)

        # Fetch the request data from S3
        request_data = get_request_from_s3(request_id)

        if is_canceled:
            # Update and save the status to CANCELED
            request_data["status"] = "CANCELED"
            request_data["message"] = "Generation canceled by the user."
            save_request_to_s3(request_id, request_data)

            return {
                "statusCode": 200,
                "body": json.dumps({
                    "status": request_data["status"],
                    "message": request_data["message"],
                    "menuItems": None,
                }),
            }

        # Simulate progress
        if request_data["status"] == "GENERATING":
            current_message = request_data["message"]
            if current_message in all_states[:-1]:
                next_index = all_states.index(current_message) + 1
                request_data["message"] = all_states[next_index]
            else:
                # Final state
                request_data["status"] = "DONE"
                request_data["message"] = "Generation complete!"
                request_data["menuItems"] = ["Item 1", "Item 2", "Item 3"]  # Example menu items

            # Save updated status to S3
            save_request_to_s3(request_id, request_data)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "status": request_data["status"],
                "message": request_data["message"],
                "menuItems": request_data["menuItems"] if request_data["status"] == "DONE" else None,
            }),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Failed to fetch generation status", "error": str(e)}),
        }
