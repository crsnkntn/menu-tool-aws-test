import json
import boto3
import uuid
from botocore.exceptions import ClientError
from lib_types import MenuItemLarge

# Initialize S3 client
s3_client = boto3.client("s3")
BUCKET_NAME = "your-s3-bucket-name"  # Replace with your S3 bucket name


def new_menu_req(data):
    """
    Handles the creation of a new menu request.
    """
    pdf_files = data.get("pdf_files", [])
    req_url = data.get("url")
    print(f"Received {len(pdf_files)} PDFs and URL: {req_url}")

    if not pdf_files and not req_url:
        return {"statusCode": 400, "body": json.dumps({"error": "No PDF files or URL provided"})}

    # Generate a new menu ID
    menu_id = str(uuid.uuid4())  # Generate a unique menu ID

    # Store initial metadata in S3 (if needed)
    metadata = {"pdf_files": pdf_files, "req_url": req_url}
    try:
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=f"menus/{menu_id}/metadata.json",
            Body=json.dumps(metadata),
            ContentType="application/json"
        )
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

    return {"statusCode": 200, "body": json.dumps({"status": "success", "menu_id": menu_id})}


def get_status(params):
    """
    Retrieves the status of a menu by menu ID.
    """
    menu_id = params.get("menu_id")
    if not menu_id:
        return {"statusCode": 400, "body": json.dumps({"error": "Missing menu ID"})}

    # Check if the menu metadata exists in S3
    try:
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=f"menus/{menu_id}/metadata.json")
        metadata = json.loads(response["Body"].read().decode("utf-8"))
    except ClientError as e:
        return {"statusCode": 404, "body": json.dumps({"error": "Menu ID not found"})}

    return {"statusCode": 200, "body": json.dumps({"status": "success", "menu_id": menu_id, "menu_metadata": metadata})}


def save_menu(data):
    """
    Saves a menu object in S3.
    """
    menu_id = data.get("menu_id")
    menu_object = data.get("menu_object")

    if not menu_id or not menu_object:
        return {"statusCode": 400, "body": json.dumps({"error": "Missing menu ID or menu object"})}

    try:
        # Validate and save the menu object
        menu = MenuItemLarge(**menu_object)
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=f"menus/{menu_id}/menu.json",
            Body=json.dumps(menu.dict()),
            ContentType="application/json"
        )
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
    except Exception as e:
        return {"statusCode": 400, "body": json.dumps({"error": f"Validation error: {e}"})}

    return {"statusCode": 200, "body": json.dumps({"status": "success", "menu_id": menu_id})}


def update_menu(data):
    """
    Updates an existing menu object in S3.
    """
    menu_id = data.get("menu_id")
    menu_object = data.get("menu_object")

    if not menu_id or not menu_object:
        return {"statusCode": 400, "body": json.dumps({"error": "Missing menu ID or menu object"})}

    try:
        # Validate and update the menu object
        menu = MenuItemLarge(**menu_object)
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=f"menus/{menu_id}/menu.json",
            Body=json.dumps(menu.dict()),
            ContentType="application/json"
        )
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
    except Exception as e:
        return {"statusCode": 400, "body": json.dumps({"error": f"Validation error: {e}"})}

    return {"statusCode": 200, "body": json.dumps({"status": "success", "menu_id": menu_id})}


def load_all_menus():
    """
    Loads all menu metadata from S3.
    """
    try:
        # List all menu objects in the S3 bucket
        response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix="menus/")
        if "Contents" not in response:
            return {"statusCode": 200, "body": json.dumps({"status": "success", "menus": []})}

        # Retrieve metadata for all menus
        menus = []
        for obj in response["Contents"]:
            if obj["Key"].endswith("menu.json"):
                menu_response = s3_client.get_object(Bucket=BUCKET_NAME, Key=obj["Key"])
                menu_data = json.loads(menu_response["Body"].read().decode("utf-8"))
                menus.append(menu_data)
    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

    return {"statusCode": 200, "body": json.dumps({"status": "success", "menus": menus})}


def lambda_handler(event, context):
    """
    Main Lambda handler function.
    """
    try:
        # Get the HTTP method and path from API Gateway
        http_method = event.get("httpMethod", "")
        path = event.get("path", "")
        query_params = event.get("queryStringParameters", {})
        body = json.loads(event.get("body", "{}"))

        # Route based on path and HTTP method
        if path == "/new-menu-req" and http_method == "POST":
            return new_menu_req(body)
        elif path == "/get-status" and http_method == "GET":
            return get_status(query_params)
        elif path == "/save-menu" and http_method == "POST":
            return save_menu(body)
        elif path == "/update-menu" and http_method == "PUT":
            return update_menu(body)
        elif path == "/load-all-menus" and http_method == "GET":
            return load_all_menus()
        else:
            return {"statusCode": 404, "body": json.dumps({"error": "Not Found"})}

    except Exception as e:
        # Handle errors gracefully
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
