# THIS FILE IS A PIECE OF WORK


import json
import boto3
import uuid
from botocore.exceptions import ClientError
from lib_types import MenuItemLarge, ImageData

# Initialize S3 client
s3_client = boto3.client("s3")
BUCKET_NAME = "menu-tool-bucket"

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


def get_test_menu():
    """
    Returns a test menu ID.
    """
    # Generate a fake menu ID for testing
    test_menu_id = str(uuid.uuid4())
    
    return {
        "statusCode": 200, 
        "body": json.dumps({
            "status": "success", 
            "menu_id": test_menu_id,
            "message": "Test menu ID generated successfully"
        })
    }


def get_test_status(menu_id):
    """
    Returns the status of the test menu, including a fake menu object.
    """
    # Create a fake menu item for testing
    fake_menu_item = MenuItemLarge(
        name="Test Item 1",
        description="A description of the test item.",
        image=ImageData(url="https://example.com/image.png", altText="Test image"),
        menuType="Main Course",
        itemType="Food",
        foodCategoryId=1,
        flashcardBack="Flashcard back content",
        dietary=["Vegetarian", "Gluten-Free"],
        allergens=["Peanuts"],
        relatedIds=["item123", "item456"],
        storeIds=[101, 102],
        shiftIds=[1, 2],
        tagIds=["vegan", "gluten_free"]
    )

    fake_menu = {
        "menu_id": menu_id,
        "menu_name": "Test Menu",
        "items": [fake_menu_item.dict()],  # Convert MenuItemLarge to a dict for the response
        "status": "completed"
    }

    return {
        "statusCode": 200, 
        "body": json.dumps({
            "status": "success", 
            "menu_id": menu_id, 
            "menu_status": "completed",
            "menu": fake_menu
        })
    }


def handler(event, context):
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
        elif path == "/test-new-menu-req" and http_method == "GET":
            return get_test_menu()
        elif path == "/test-get-status" and http_method == "GET":
            return get_test_status()
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
