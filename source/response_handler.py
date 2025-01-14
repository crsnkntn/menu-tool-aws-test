from flask import Flask, request, jsonify
from flask_cors import CORS
import re
from source.crawler import Crawler
from source.process_link import process_pdf, process_urls, chunk_text_data
from source.gen_items import ItemGenerator, ItemExpander, MenuItemSmall, MenuItemLarge


class ResponseHandler:
    def __init__(self, base_url: str):
        self.url = base_url

    def handle_request(self):
        crawler = Crawler(self.url)
        print(f"Crawling URL: {self.url}")
        crawler.crawl()
        all_links, pdf_links, relevant_links = crawler.get_results()

        print(f"Processing {len(pdf_links)} PDF links.")
        pdf_text = [process_pdf(link) for link in pdf_links if link]

        print(f"Processing {len(relevant_links)} webpage links.")
        webpage_text = process_urls(relevant_links)

        pdf_text = [text for text in pdf_text if text]
        webpage_text = [text for text in webpage_text if text]

        chunks = chunk_text_data(pdf_text, webpage_text, chunk_size=100000)
        print(f"Created {len(chunks)} chunks from the processed text.")

        items = []
        for i, chunk in enumerate(chunks):
            print(f"Processing chunk #{i + 1}/{len(chunks)}")
            gen = ItemGenerator()
            items.extend([MenuItemSmall(**item) for item in gen(chunk)])

        item_expand = ItemExpander()
        menu_items = []
        for item in items:
            expanded_item = item_expand.expand(item)
            if isinstance(expanded_item, MenuItemLarge):
                menu_items.append(expanded_item)
            else:
                print(f"Failed to expand item: {item}")

        serialized_menu_items = [item.model_dump() for item in menu_items if item]
        
        return {
            "pdf_urls": pdf_links,
            "webpage_urls": relevant_links,
            "menu_items": serialized_menu_items
        }