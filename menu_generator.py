import os
import uuid
import boto3
import pytesseract
from PIL import Image
from PyPDF2 import PdfReader
from basemodel_types import *

# S3 configuration
S3_BUCKET = "menu-tool-bucket"
S3_REGION = "us-east-2"
s3_client = boto3.client("s3", region_name=S3_REGION)

def update_status(
    request_id: str, 
    status: str, 
    progress: str, 
    message: str
):
    """
    Update the status and message in S3 for the given request_id.
    """
    status_data = {
        "status": status,
        "progress": progress,
        "message": message,
    }
    try:
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=f"status/{request_id}.json",
            Body=json.dumps(status_data),
            ContentType="application/json",
        )
        print(f"Status updated for {request_id}: {status_data}")
    except Exception as e:
        print(f"Error updating status for {request_id}: {e}")

# Temporary directory for local file storage
TEMP_DIR = "/tmp/menu_tool"
os.makedirs(TEMP_DIR, exist_ok=True)

# Generation Variables
CHUNK_SIZE = 500


class MenuGenerator:
    '''
    Generates items based on the provided url and requested files

    url: string # properly formatted url string
    file_keys: list[string] # list of s3 keys for each file
    request_id: string # unique id for this request; used to read/write from/to the s3 bucket
    '''
    def __init__(
        self, 
        url: str, 
        file_keys: list, 
        request_id: str
    ):
        self.url = url.strip() if url else None
        self.file_keys = file_keys
        self.request_id = request_id

    def generate(
        self, 
        chunk_size: int = CHUNK_SIZE
    ):
        """
        Execute all steps to generate expanded menu items:
        1. Extract all content from the files provided
        2. Extract all content from the URL provided
        3. Clean/combine text segments into chunks
        4. Generate PartialItems from the chunks
        5. Standardize menu categories
        6. Expand well-formed PartialItems into FullItems

        Returns the expanded menu items.
        """
        # Step 1: Extract all content from the files provided
        update_status(self.request_id, "processing", "10%", "Extracting content from files...")
        raw_text_segments = self.get_relevant_text_from_files()

        # Step 2: Extract all content from the URL provided
        if self.url:
            update_status(self.request_id, "processing", "30%", "Extracting content from URL...")
            url_segments = self.get_relevant_text_from_url(self.url)
            raw_text_segments.extend(url_segments)

        # Step 3: Clean and chunk all relevant text
        update_status(self.request_id, "processing", "50%", "Cleaning and chunking text segments...")
        chunks = self.clean_text_segments(raw_text_segments)

        # Step 4: Generate PartialItems from the chunks
        update_status(self.request_id, "processing", "70%", "Generating menu item templates...")
        menu_items_small, running_category_list = self.generate_menu_templates(chunks)

        # Step 5: Standardize menu categories
        update_status(self.request_id, "processing", "80%", "Standardizing menu categories...")
        from openai_functions import standardize_categories
        final_categories = standardize_categories(running_category_list)

        # Step 6: Expand well-formed PartialItems into FullItems
        update_status(self.request_id, "processing", "90%", "Expanding menu item templates...")
        expanded_items = self.expand_menu_templates(menu_items_small, final_categories)

        update_status(self.request_id, "completed", "100%", "Menu generation complete!")
        return expanded_items

    def download_file_from_s3(
        self, 
        file_key: str
    ) -> str:
        local_path = os.path.join(TEMP_DIR, os.path.basename(file_key))
        try:
            s3_client.download_file(S3_BUCKET, file_key, local_path)
            return local_path
        except Exception as e:
            print(f"Error downloading {file_key} from S3: {e}")
            return None

    def create_pdf_from_image(
        self, 
        image_path: str
    ) -> str:
        '''
        1. Uses tesseract to convert image to a pdf
        2. Returns the path to that pdf
        '''
        try:
            image = Image.open(image_path)
            pdf_bytes = pytesseract.image_to_pdf_or_hocr(image, extension='pdf')
            pdf_path = os.path.join(TEMP_DIR, f"{uuid.uuid4()}.pdf")
            with open(pdf_path, 'wb') as f:
                f.write(pdf_bytes)
            return pdf_path
        except Exception as e:
            print(f"Error converting image {image_path} to PDF: {e}")
            return None

    def extract_text_from_pdf(
        self, 
        pdf_path: str
    ) -> str:
        '''
        1. Use PdfReader to extract all text from the pdf
        2. Return the list of extracted text
        '''
        try:
            reader = PdfReader(pdf_path)
            full_text = ""
            for page in reader.pages:
                page_text = page.extract_text() or ""
                full_text += page_text
            return full_text
        except Exception as e:
            print(f"Error extracting text from PDF {pdf_path}: {e}")
            return ""

    def get_relevant_text_from_files(
        self
    ) -> list:
        '''
        1. Iterate through the files and handle them according to their kind
        2. Append all content to a list and return
        '''
        raw_text_segments = []
        for file_key in self.file_keys:
            local_path = self.download_file_from_s3(file_key)
            if not local_path:
                continue

            ext = os.path.splitext(local_path)[1].lower()
            # TODO: add compatibility for all text-based files
            if ext == ".pdf":
                text = self.extract_text_from_pdf(local_path)
                if text:
                    raw_text_segments.append(text)
            elif ext in [".jpg", ".jpeg", ".png", ".bmp", ".gif"]:
                pdf_path = self.create_pdf_from_image(local_path)
                if pdf_path:
                    text = self.extract_text_from_pdf(pdf_path)
                    if text:
                        raw_text_segments.append(text)
            else:
                print(f"Unsupported file type for {local_path}")

        return raw_text_segments

    def get_relevant_text_from_url(
        self, 
        url: str
    ) -> list:
        '''
        1. Use the Crawler to find all relevant pdfs and html content
        2. Extract the relevant content from the pdfs
        3. Extract the relevant content from the html
        '''
        try:
            from crawler import Crawler
            from process_text import process_pdf, extract_content_from_html
            crawler = Crawler(url)
            relevant_links, pdf_links = crawler.crawl()
            pdf_texts = [process_pdf(link) for link, _ in pdf_links if link]
            pdf_texts = [s for s in pdf_texts if s]
            webpage_text = []
            for link, html in relevant_links:
                if link and html:
                    webpage_text.extend(extract_content_from_html(html))
            return webpage_text + pdf_texts
        except Exception as e:
            print(f"Error processing URL {url}: {e}")
            return []

    def clean_text_segments(
        self, 
        segments: list, 
        chunk_size: int = CHUNK_SIZE
    ) -> list:
        from process_text import chunk_text_data
        return chunk_text_data(segments, chunk_size=chunk_size)

    def generate_menu_templates(
        self, 
        chunks: list
    ) -> (list, list):
        """
        Generate PartialItems from text chunks
        Generate a list of all categories seen TODO: VERY BROKEN RIGHT NOW
        Return the PartialItems and the list
        """
        menu_items_small = []
        running_category_list = []
        from openai_functions import generate_items
        from basemodel_types import PartialItem
        for chunk in chunks:
            try:
                chunk_items, running_category_list = generate_items(chunk, running_category_list)
                small_items = [PartialItem(**item) for item in chunk_items]
                menu_items_small.extend(small_items)
            except Exception as e:
                print(f"Error generating menu items from chunk: {e}")
        return menu_items_small, running_category_list

    def expand_menu_templates(
        self, 
        items: list, 
        item_categories: list
    ) -> list:
        '''
        1. Remove duplicate and malformed PartialItems
        2. Generate FullItems from the well-formed Partialitems
        3. Return FullItems
        '''
        # Remove duplicates based on item name.
        seen = set()
        unique_items = []
        for item in items:
            key = item.name.strip().lower()
            # TODO: add more robust malformation detection
            if key not in seen or key == "":
                unique_items.append(item)
                seen.add(key)

        expanded_items = []
        from openai_functions import expand_item
        # TODO: allow the user to hardcode the categories!
        # Hardcoded allergens and dietary options.
        allergens = [
            "Milk", "Eggs", "Peanuts", "Walnuts", "Tree nuts", "Soy",
            "Wheat", "Fish", "Shellfish", "Sesame"
        ]
        dietary = [
            "Vegetarian", "Vegan", "Gluten-Free", "Dairy-Free", "Nut-Free",
            "Soy-Free", "Keto", "Paleo", "Low-Carb", "Low-Sodium", "Halal", "Kosher"
        ]
        for item in unique_items:
            try:
                expanded = expand_item(item, item_categories, allergens, dietary)
                if expanded:
                    expanded_items.append(expanded)
            except Exception as e:
                print(f"Error expanding menu item {item.name}: {e}")
        return expanded_items



if __name__ == "__main__":
    gen = MenuGenerator("https://www.eatathazels.com", [], "test_id")
    gen.generate()