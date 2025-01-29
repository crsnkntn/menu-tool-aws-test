from crawler import Crawler
from process_text import process_pdf, extract_content_from_html, chunk_text_data
from lib_types import MenuItemSmall, MenuItemLarge
from openai_functions import *
import re
import boto3
from tqdm import tqdm
from statistics import mean

class GenerateMenuHandler:
    S3_BUCKET = "menu-tool-bucket"
    s3_client = boto3.client("s3")
    
    all_states = [
        "Crawling & Scraping the Page ...",
        "Cleaning the Scraped Content ...",
        "Generating the Menu Item Templates ...",
        "Expanding the Menu Item Templates ...",
        "Cleaning and Refining all Menu Items ..."
    ]
    
    def __init__(self, url: str, request_id: str):
        self.url = url.strip()
        # Use regex to extract the core part of the link (e.g., 'example')
        match = re.search(r"(?:https?://)?(?:www\.)?([^/]+)", self.url)
        if match:
            core_link = match.group(1)
            self.url = f"https://www.{core_link}.com"
        else:
            return None
        self.request_id = request_id
        self.request_data = {
            "status": "GENERATING",
            "message": self.all_states[0],
            "menuItems": None,
        }
        self.save_request_to_s3()
    
    def run(self):
        """Execute all menu generation steps in order, updating S3 at each step."""
        try:
            pairs = self.get_url_html_pairs(self.url)
            chunks = self.clean_url_html_pairs(pairs)
            items, categories = self.generate_menu_templates(chunks)
            expanded_items = self.expand_menu_templates(items)
            self.standardize_menu_items(expanded_items)
        except Exception as e:
            self.request_data["status"] = "FAILED"
            self.request_data["message"] = f"Error occurred: {str(e)}"
            self.save_request_to_s3()

    def save_request_to_s3(self):
        """Save the request object to S3."""
        try:
            self.s3_client.put_object(
                Bucket=self.S3_BUCKET,
                Key=f"requests/{self.request_id}.json",
                Body=json.dumps(self.request_data),
                ContentType="application/json",
            )
        except ClientError as e:
            raise Exception(f"Error saving to S3: {e}")
    
    def update_status(self, state_index: int):
        """Update the current status message."""
        self.request_data["message"] = self.all_states[state_index]
        self.save_request_to_s3()
    
    def finalize_generation(self, menu_items):
        """Mark the request as completed with final menu items."""
        self.request_data["status"] = "DONE"
        self.request_data["message"] = "Generation complete!"
        self.request_data["menuItems"] = menu_items
        self.save_request_to_s3()
    
    def get_url_html_pairs(self):
        self.update_status(0)
        crawler = Crawler(self.url)
        relevant_links, pdf_links = crawler.crawl()
        pdf_text = [process_pdf(link) for link, _ in pdf_links if link]
        pdf_text = [s for s in pdf_text if s]
        webpage_text = []
        for link, html in relevant_links:
            if link and html:
                webpage_text.extend(extract_content_from_html(html))
        return webpage_text + pdf_text
    
    def clean_url_html_pairs(self, pairs):
        self.update_status(1)
        chunks = chunk_text_data(pairs, chunk_size=500)
        return chunks
    
    def generate_menu_templates(self, chunks):
        self.update_status(2)
        items = []
        categories = []
        for chunk in tqdm(chunks, desc="Processing chunks!"):
            chunk_items, categories = generate_items(chunk, categories)
            items.extend([MenuItemSmall(**item) for item in chunk_items])
        return items, categories
    
    def expand_menu_templates(self, templates):
        self.update_status(3)
        categories, allergens, diets = standardize_categories([]), [
            "Milk", "Eggs", "Peanuts", "Walnuts", "Tree nuts", "Soy",
            "Wheat", "Fish", "Shellfish", "Sesame"
        ], [
            "Vegetarian", "Vegan", "Gluten-Free", "Dairy-Free", "Nut-Free",
            "Soy-Free", "Keto", "Paleo", "Low-Carb", "Low-Sodium",
            "Halal", "Kosher"
        ]
        seen_names = set()
        unique_items = []
        for item in templates:
            if item.name.lower() not in seen_names:
                unique_items.append(item)
                seen_names.add(item.name.lower())
        menu_items = []
        for item in tqdm(unique_items, desc="Expanding menu items"):
            expanded_item = expand_item(item, categories, allergens, diets)
            if isinstance(expanded_item, MenuItemLarge):
                menu_items.append(expanded_item)
        return menu_items
    
    def standardize_menu_items(self, items):
        self.update_status(4)
        serialized_menu_items = [
            item.dict() for item in items if isinstance(item, MenuItemLarge)
        ]
        self.finalize_generation(serialized_menu_items)
