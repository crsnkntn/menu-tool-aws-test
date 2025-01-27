from crawler import Crawler
from process_text import process_pdf, extract_content_from_html, chunk_text_data
from lib_types import MenuItemSmall, MenuItemLarge
from openai_functions import *
import re
from tqdm import tqdm
from statistics import mean

def writefile(thing, filename="testing_output/output.txt"):
    with open(filename, "a+", encoding="utf-8") as file:
        file.write(thing + "\n")

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
        relevant_links, pdf_links = crawler.crawl()

        writefile("\nLINKS TO BE SCRAPED:")
        for link, html in relevant_links:
            writefile(f"{link}\n{html}")

        pdf_text = [process_pdf(link) for link, _ in pdf_links if link]
        pdf_text = [s for s in pdf_text if s]

        webpage_text = []
        for link, html in relevant_links:
            if link and html:
                webpage_text.extend(extract_content_from_html(html))

        all_text = [s.replace('\n', " ") for s in (webpage_text + pdf_text) if s]

        # TODO: CHANGE THIS FUNCTION
        chunks = chunk_text_data(all_text, chunk_size=500)
        print(f"Created {len(chunks)} chunks from the processed text.")

        items = []
        categories = []
        allergens = [
            "Milk",
            "Eggs",
            "Peanuts",
            "Walnuts",
            "Tree nuts",
            "Soy",
            "Wheat",
            "Fish",
            "Shellfish",
            "Sesame"
        ]
        diets = [
            "Vegetarian",
            "Vegan",
            "Gluten-Free",
            "Dairy-Free",
            "Nut-Free",
            "Soy-Free",
            "Keto",
            "Paleo",
            "Low-Carb",
            "Low-Sodium",
            "Halal",
            "Kosher"
        ]

        for chunk in tqdm(chunks, desc="Processing chunks!"):
            # Use the generate_items function
            chunk_items, categories = generate_items(chunk, categories)
            items.extend([MenuItemSmall(**item) for item in chunk_items])


        # Standardize the category lists
        print(f"BEFORE____{categories}\n{allergens}\n{diets}\n")
        categories = standardize_categories(categories)
        print(f"AFTER____{categories}\n{allergens}\n{diets}\n")

        # Remove duplicates based on item names
        seen_names = set()
        unique_items = []

        for item in items:
            if item.name.lower() not in seen_names:
                unique_items.append(item)
                seen_names.add(item.name.lower())

        menu_items = []
        for item in tqdm(unique_items, desc="Expanding menu items"):
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
