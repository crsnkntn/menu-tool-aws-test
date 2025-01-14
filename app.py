from flask import Flask, request, jsonify
from flask_cors import CORS
import re
from source.response_handler import ResponseHandler

app = Flask(__name__)

# UNCOMMENT FOR LOCAL TESTING
#CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})

@app.route('/process_request', methods=['POST'])
def process_request():
    data = request.get_json()
    req_url = data.get("url")
    if not req_url:
        return jsonify({"error": "Missing URL"}), 400

    match = re.search(r"([a-zA-Z0-9-]+)\.com", req_url)
    if match:
        domain = match.group(1)
        req_url = f"https://{domain}.com"
    else:
        return jsonify({"error": "Improperly formatted URL"}), 400

    handler = ResponseHandler(req_url)
    response = handler.handle_request()

    return jsonify({
        "status": "completed",
        "original_url": req_url,
        **response,
        "log_file": "server.log",
    }), 200


# test endpoint
@app.route('/test_endpoint', methods=['GET'])
def test_endpoint():
    return jsonify({"status": "success", "message": "Test endpoint is working!"}), 200


if __name__ == "__main__":
    app.run(debug=True, port=5000)
