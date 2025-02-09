from pydantic import BaseModel
from typing import List

from abc import ABC, abstractmethod

class MenuGenerator(ABC):
    """Abstract base class for menu generation from different sources."""

    @abstractmethod
    def generate_items(self, source: str):
        """Generates menu items from a given source (image, PDF, or URL)."""
        pass

# REQUIREMENTS
# - Accept any type of image/text file
# - Accept url
# - image filenames are consistent to the return object and s3 bucket


'''
Notes before bed

the endpoint should create menugenerators from the passed in data

each generator will create a list of simple items

then these simple items will be added to a set

this set will be used to create the list of categories (might have to add categories to simpleitem)

these simple items are expanded and this object is returned, voila

'''


class ImageData(BaseModel):
    file: str
    filename: str


class PartialItem(BaseModel):
    name: str
    description: str
    image: ImageData
    details: List[str]

    def __eq__(self, other):
        if isinstance(other, PartialItem):
            return self.name.strip().lower() == other.name.strip().lower()
        return False

    def __hash__(self):
        return hash(self.name.strip().lower())

class FullItem(BaseModel):
    name: str
    description: str
    image: ImageData
    menuType: str
    itemType: str
    foodCategoryId: str
    flashcardBack: str
    dietary: List[str]
    allergens: List[str]
    relatedIds: List[str]
    storeIds: List[int]
    shiftIds: List[int]
    tagIds: List[str]


# TODO
def process_local_image(image_path):
    # convert the image to a pdf
    pdf_path = image_path

    return process_pdf(pdf_path)

# TODO
def process_local_pdf(pdf_path):
    pass


def fetch_html_content(url):
    pass

# returns chunked text and discovered links
def clean_html_content(content):
    pass


def generate_simple_items(text):
    pass


class MenuGeneratorFromImage(MenuGenerator):
    def generate_items(self, source: str):
        return ["Item1", "Item2", "Item3"]


class MenuGeneratorFromPDF(MenuGenerator):
    def generate_items(self, source: str):
        return ["ItemA", "ItemB", "ItemC"]


class MenuGeneratorFromURL(MenuGenerator):
    def __init__(self, base_url):
        self.seen_links = set(str)
        self.simple_items = set(PartialItem)
        self.finished_items = List[FullItem]

        self.base_url = base_url
        self.core_url = get_core_url(base_url)

    # Use re to get the core url out
    def get_core_url(url):
        return url

    def expand_leaf(self, url):
        # if different
        if url.endswith(".pdf"):
            # download the pdf locally
            pdf_file = "temp.pdf"

            # Process it
            cleaned_text = process_local_pdf(pdf_file)

            # delete the temp file
            
            
        if get_core_url(url) == self.core_url and url not in self.seen_links:
            print(f"PROCESSING[{url}]")
            content = fetch_html_content(url)
            cleaned_text, discovered_links = clean_html_content(content)
            generated_items = generate_simple_items(cleaned_text)
            
            # Add the simple items to the 
            self.simple_items.add(generated_items)
            
            # Expand on the other links
            for link in discovered_links:
                expand_leaf(link)

            
        print(f"DEADEND[{url}]")

    
    def expand_simple_item(self, item):
        pass

    def generate_items(self):
        expand_leaf(self.base_url)

        for item in list(self.simple_items):
            expand_simple_item(item)

        return self.finished_items





