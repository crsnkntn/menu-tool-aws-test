from crawler import Crawler
from process_text import process_pdf, extract_content_from_html, chunk_text_data
from lib_types import MenuItemSmall, MenuItemLarge
from openai_functions import *
import re
from tqdm import tqdm
from statistics import mean

class ResponseHandler:
    def __init__(self, base_url: str):
        self.url = base_url.strip()

        # Use regex to extract the core part of the link (e.g., 'example')
        match = re.search(r"(?:https?://)?(?:www\.)?([^/]+)", self.url)
        if match:
            core_link = match.group(1)
            self.url = f"https://www.{core_link}.com"
        else:
            return None

    def handle_request(self):
        crawler = Crawler(self.url)
        print(f"Crawling URL: {self.url}")
        crawler.crawl()

        relevant_links, pdf_links = crawler.get_results()

        pdf_text = [process_pdf(link) for link, _ in pdf_links if link]
        pdf_text = [s for s in pdf_text if s]

        webpage_text = []
        for link, html in relevant_links:
            if link and html:
                webpage_text.extend(extract_content_from_html(html))

        with open("webpage.txt", "w", encoding="utf-8") as file:
            for string in webpage_text:
                file.write(string + "\n")

        with open("pdf.txt", "w", encoding="utf-8") as file:
            for string in pdf_text:
                file.write(string + "\n")

        all_text = [s.replace('\n', " ") for s in (webpage_text + pdf_text) if s]

        return

        # TODO: CHANGE THIS FUNCTION
        chunks = chunk_text_data(pdf_text, webpage_text, chunk_size=1000)
        print(f"Created {len(chunks)} chunks from the processed text.")

        items = []
        categories = []
        allergens = []
        diets = []
        for i, chunk in enumerate(chunks):
            print(f"Processing chunk #{i + 1}/{len(chunks)}")
            # Use the generate_items function
            chunk_items, categories, allergens, diets = generate_items(chunk, categories, allergens, diets)
            items.extend([MenuItemSmall(**item) for item in chunk_items])

        menu_items = []
        for item in tqdm(items, desc="Expanding menu items"):
            # Use the expand_item function
            expanded_item = expand_item(item, categories, allergens, diets)
            if isinstance(expanded_item, MenuItemLarge):
                menu_items.append(expanded_item)
            else:
                print(f"Failed to expand item: {item}")

        serialized_menu_items = [
            item.dict() for item in menu_items if isinstance(item, MenuItemLarge)
        ]
        
        return {
            "pdf_urls": pdf_links,
            "webpage_urls": relevant_links,
            "menu_items": serialized_menu_items
        }
