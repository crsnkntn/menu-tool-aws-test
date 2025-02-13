import json
import boto3
import threading
import uuid
import time
from flask_cors import CORS
from flask import Flask, request, jsonify
from menu_generator import MenuGenerator

app = Flask(__name__)
CORS(app)

# AWS S3 Configuration
S3_BUCKET = "menu-tool-bucket"
S3_REGION = "us-east-2"
s3_client = boto3.client("s3")

def _build_cors_preflight_response(methods):
    response = jsonify({"message": "CORS preflight successful"})
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Methods", methods)
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token")
    return response

   
'''
TESTS THE ACCESSIBILITY OF THE SERVER
'''
@app.route("/test", methods=["GET", "OPTIONS"])
def test():
    if request.method == "OPTIONS":
        return _build_cors_preflight_response()

    return jsonify({"message": "Flask is working!"})

'''
INITIATES MENU GENERATION PROCESS
- HEADER EXPECTATIONS:
    - url: string
    - files: list[] (I'm not sure what the type is, but add the files using Next.js's FormData)
'''
@app.route("/gen-menu", methods=["POST", "OPTIONS"])
def gen_menu():
    if request.method == "OPTIONS":
        return _build_cors_preflight_response("OPTIONS,GET,POST")

    # Get the url and files from the request object
    url = request.form.get("url")
    files = request.files.getlist("files")

    # If there is no url or no files, send a 400
    if not url and not files:
        return jsonify({"error": "Missing 'url' or 'files' parameter"}), 400

    # Create a request_id
    request_id = str(uuid.uuid4())

    # Save files to S3
    file_keys = []
    for file in files:
        s3_key = f"uploads/{request_id}/{file.filename}"
        try:
            s3_client.upload_fileobj(file, S3_BUCKET, s3_key)
            file_keys.append(s3_key)
        except Exception as e:
            return jsonify({"error": f"Failed to upload file '{file.filename}': {str(e)}"}), 500

    # Start menu generation in a separate thread
    menu_generator = MenuGenerator(url, file_keys, request_id)
    thread = threading.Thread(target=menu_generator.generate)
    thread.start()

    return jsonify({"request_id": request_id})


'''
RETRIEVES THE STATUS OF THE GENERATION PROCESS
'''
@app.route("/status/<request_id>", methods=["GET", "OPTIONS"])
def get_status(request_id):
    # Handle the preflight response
    if request.method == "OPTIONS":
        return _build_cors_preflight_response("OPTIONS,GET")

    # Try to get the status
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=f"status/{request_id}.json")
        status_data = json.loads(response["Body"].read().decode("utf-8"))
        return jsonify(status_data)
    except s3_client.exceptions.NoSuchKey:
        return jsonify({"error": "Request ID not found or still processing"}), 404
    except Exception as e:
        return jsonify({"error": f"Failed to fetch status: {str(e)}"}), 500


'''
GET THE GENERATED MENU

If this is called before the generation process is done, it will return an empty list
'''
@app.route("/get-menu", methods=["GET", "OPTIONS"])
def get_menu():
    if request.method == "OPTIONS":
        return _build_cors_preflight_response("OPTIONS,GET")

    request_id = request.args.get("request_id")
    if not request_id:
        return jsonify({"error": "Missing 'request_id' parameter"}), 400

    try:
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=f"results/{request_id}.json")
        menu_data = json.loads(response["Body"].read().decode("utf-8"))
        return jsonify(menu_data)
    except s3_client.exceptions.NoSuchKey:
        return jsonify({"error": "Request ID not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Failed to fetch menu: {str(e)}"}), 500
        

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
