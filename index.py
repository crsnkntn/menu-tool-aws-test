import json
import time

# Simulated in-memory storage for request status
generation_requests = {}

def handler(event, context):
    try:
        # Parse the HTTP method and path
        http_method = event.get("httpMethod", "")
        path = event.get("path", "")

        if http_method == "POST" and path == "/generate-menu":
            return handle_generate_request(event)

        if http_method == "GET" and path.startswith("/generation-status/"):
            return handle_generation_status(event)

        return {
            "statusCode": 404,
            "body": json.dumps({"message": "Not Found"})
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"message": str(e)})
        }


def handle_generate_request(event):
    """Handles the initial request to generate a menu."""
    body = json.loads(event.get("body", "{}"))
    text = body.get("text", "")
    pdf_files = body.get("pdfFiles", [])

    if not text or not pdf_files:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "Text and PDF files are required"})
        }

    # Generate a unique request ID
    request_id = f"request_00000000"

    # Store the initial status
    generation_requests[request_id] = {
        "status": "GENERATING",
        "progress": 0,
        "message": "Generation started. Please wait...",
        "menuItems": None
    }

    return {
        "statusCode": 200,
        "body": json.dumps({"requestId": request_id})
    }


def handle_generation_status(event):
    """Handles polling for the generation status."""
    path = event.get("path", "")
    request_id = path.split("/")[-1]

    if request_id not in generation_requests:
        return {
            "statusCode": 404,
            "body": json.dumps({"message": "Request ID not found"})
        }

    # Simulate progress
    request_status = generation_requests[request_id]
    if request_status["status"] == "GENERATING":
        request_status["progress"] += 1

        if request_status["progress"] >= 4:
            # Mark as done after 4 updates
            request_status["status"] = "DONE"
            request_status["message"] = "Generation complete!"
            request_status["menuItems"] = [
                {"name": "Burger", "description": "A delicious burger", "price": "$10"},
                {"name": "Pizza", "description": "Cheesy pepperoni pizza", "price": "$15"},
                {"name": "Salad", "description": "Fresh garden salad", "price": "$8"}
            ]
        else:
            request_status["message"] = f"Generation in progress... Step {request_status['progress']} of 4."

    return {
        "statusCode": 200,
        "body": json.dumps({
            "status": request_status["status"],
            "message": request_status["message"],
            "menuItems": request_status.get("menuItems", None)
        })
    }
