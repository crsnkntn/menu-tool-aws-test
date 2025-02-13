from flask import Flask, request, jsonify, Response
from verify_aws_sig import verify_aws_signature
from menu_generator import MenuGenerator
import os
import uuid
import threading
import time
import boto3
import json
from flask_cors import CORS
from werkzeug.utils import secure_filename

app = Flask(__name__)

# AWS S3 Configuration
S3_BUCKET = "menu-tool-bucket"
S3_REGION = "us-east-2"
s3_client = boto3.client("s3")

# Allowed file types
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}

def allowed_file(filename):
    """Check if a file extension is allowed."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/test", methods=["GET"])
def test():
    return jsonify({"hello": "its working"})

@app.route("/gen-menu", methods=["POST"])
def gen_menu():
    """Accepts a URL and files, stores them in S3, and starts menu generation."""
    # Verify AWS Signature
    is_valid, message = verify_aws_signature(request)
    if not is_valid:
        return jsonify({"error": message}), 403

    # Extract URL
    data = request.form
    url = data.get("url")
    if not url:
        return jsonify({"error": "Missing 'url' parameter"}), 400

    # Generate a unique request_id
    request_id = str(uuid.uuid4())

    # Handle multiple file uploads & upload them to S3
    files = request.files.getlist("files")
    uploaded_files = []

    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(f"{request_id}_{file.filename}")
            s3_client.upload_fileobj(file, S3_BUCKET, f"uploads/{filename}")
            file_url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/uploads/{filename}"
            uploaded_files.append(file_url)
        else:
            return jsonify({"error": f"Invalid file type: {file.filename}"}), 400

    # Update request status in S3
    update_status(request_id, "processing", "Menu generation started")

    # Run menu generation in the background
    thread = threading.Thread(target=process_menu_generation, args=(request_id, url, uploaded_files))
    thread.start()

    return jsonify({"request_id": request_id})


def process_menu_generation(request_id, url, files):
    """Simulate menu generation and store the result in S3."""
    try:
        time.sleep(2)  # Simulate some processing time
        #generator = MenuGenerator(url, files)
        update_status(request_id, "working", "Menu is forming")
        
        menu_data = {
            "request_id": request_id,
            "url": url,
            "files": files,
            "menu": [
                {"item": "Burger", "price": 9.99, "category": "Main Course"},
                {"item": "Fries", "price": 3.99, "category": "Side"},
                {"item": "Soda", "price": 1.99, "category": "Beverage"},
                {"item": "Salad", "price": 7.99, "category": "Healthy Option"},
            ],
            "status": "completed",
            "message": "Fake menu generated successfully"
        }

        # Save result in S3 as JSON
        menu_json = json.dumps(menu_data)
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=f"results/{request_id}.json",
            Body=menu_json,
            ContentType="application/json"
        )

        # Update request status in S3
        update_status(request_id, "completed", "Menu generated successfully")

    except Exception as e:
        update_status(request_id, "failed", str(e))


@app.route("/status/<request_id>", methods=["GET"])
def get_status(request_id):
    """Streams status updates for a given request_id."""
    def event_stream():
        while True:
            status_info = get_status_from_s3(request_id)
            if status_info:
                yield f"data: {json.dumps(status_info)}\n\n"
                if status_info["status"] in ["completed", "failed"]:
                    break  # Stop streaming when request completes
            time.sleep(1)

    return Response(event_stream(), mimetype="text/event-stream")


@app.route("/get-menu", methods=["GET"])
def get_menu():
    """Retrieves menu data from S3 using request_id."""
    # Verify AWS Signature
    is_valid, message = verify_aws_signature(request)
    if not is_valid:
        return jsonify({"error": message}), 403

    request_id = request.args.get("request_id")
    if not request_id:
        return jsonify({"error": "Missing 'request_id' parameter"}), 400

    # Retrieve menu from S3
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=f"results/{request_id}.json")
        menu_data = json.loads(response["Body"].read().decode("utf-8"))
        return jsonify({"request_id": request_id, "menu": menu_data})

    except s3_client.exceptions.NoSuchKey:
        return jsonify({"error": "Request ID not found or still processing"}), 404


def update_status(request_id, status, message):
    """Stores request status in S3."""
    status_data = {"status": status, "message": message}
    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=f"status/{request_id}.json",
        Body=json.dumps(status_data),
        ContentType="application/json"
    )


def get_status_from_s3(request_id):
    """Retrieves request status from S3."""
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=f"status/{request_id}.json")
        return json.loads(response["Body"].read().decode("utf-8"))
    except s3_client.exceptions.NoSuchKey:
        return None


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
