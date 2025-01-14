from flask import Flask, request, jsonify
from flask_cors import CORS
import re
import logging
import json
import os
from datetime import datetime

from source.crawler import Crawler
from source.process_link import process_pdf, process_urls, chunk_text_data
from source.gen_items import ItemGenerator, ItemExpander, MenuItemSmall, MenuItemLarge

app = Flask(__name__)

# TODO: update this for deployment
CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})

# TODO: set up the logger
logger = None

@app.route('/process_request', methods=['POST'])
def process_request():
    # Get the URL from the request object
    data = request.get_json()
    req_url = data.get("url")
    if not req_url:
        return jsonify({"error": "Missing URL"}), 400

    # Ensure the URL is formatted correctly
    match = re.search(r"([a-zA-Z0-9-]+)\.com", req_url)
    if match:
        domain = match.group(1)
        req_url = f"https://{domain}.com"
    else:
        return jsonify({"error": "Improperly formatted URL"}), 400

    # Crawl the URL and retrieve links
    crawler = Crawler(req_url)
    print(f"Crawling URL: {req_url}")
    crawler.crawl()
    all_links, pdf_links, relevant_links = crawler.get_links()

    # Process the links
    print(f"Processing {len(pdf_links)} PDF links.")
    pdf_text = [process_pdf(link) for link in pdf_links if link]

    print(f"Processing {len(relevant_links)} webpage links.")
    webpage_text = process_urls(relevant_links)

    # Ensure non-empty text lists are passed
    pdf_text = [text for text in pdf_text if text]  # Filter out empty results
    webpage_text = [text for text in webpage_text if text]  # Filter out empty results

    print(len(pdf_text))
    print(len(webpage_text))
    # Chunk the text data
    chunks = chunk_text_data(pdf_text, webpage_text, chunk_size=100000)
    print(f"Created {len(chunks)} chunks from the processed text.")

    # Generate the small menu items from the chunks of data
    items = []
    for i, chunk in enumerate(chunks):
        print(f"Processing chunk #{i + 1}/{len(chunks)}")
        gen = ItemGenerator()
        items.extend([MenuItemSmall(**item) for item in gen(chunk)])

    # Expand the items
    item_expand = ItemExpander()
    menu_items = []
    for item in items:
        expanded_item = item_expand.expand(item)
        if isinstance(expanded_item, MenuItemLarge):
            menu_items.append(expanded_item)
        else:
            print(f"Failed to expand item: {item}")

    serialized_menu_items = [item.model_dump() for item in menu_items if item]

    # Return the results
    return jsonify({
        "status": "completed",
        "original_url": req_url,
        "pdf_urls": pdf_links,
        "webpage_urls": relevant_links,
        "menu_items": serialized_menu_items,
        "log_file": "server.log",
    }), 200



if __name__ == "__main__":
    app.run(debug=True, port=5000)
