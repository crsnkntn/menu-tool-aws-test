from openai import OpenAI
from pydantic import BaseModel
from typing import List, Dict, Any
from dotenv import load_dotenv
import os
import json

# Load environment variables
load_dotenv()

# Initialize OpenAI client with API key from .env file
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

gpt_model = "gpt-4o-mini"


# Define models
class ImageData(BaseModel):
    file: str
    filename: str


class MenuItemSmall(BaseModel):
    name: str
    description: str
    image: ImageData
    details: list[str]


# Used as the response type for gpt
class SmallResponse(BaseModel):
    items: list[MenuItemSmall]


class MenuItemLarge(BaseModel):
    name: str
    description: str
    image: ImageData
    menuType: str
    itemType: str
    foodCategoryId: int
    flashcardBack: str
    dietary: list[str]
    allergens: list[str]
    relatedIds: list[str]
    storeIds: list[int]
    shiftIds: list[int]
    tagIds: list[str]

class LargeResponse(BaseModel):
    items: list[MenuItemLarge]


class ItemGenerator:
    def __init__(self):
        self.prompt_template = (
            "The following text is scraped from a restaurant's website. Some of the content may include information about menu items, "
            "but most of it may not be relevant. Your task is to identify and extract details about the menu items from this text. "
            "If no menu data is found in the provided text, return an empty list. "
            "\n\n"
            "Include beer and wine as well"
            "For each menu item, include the following information:\n"
            "- Name\n"
            "- Description\n"
            "- Category or dietary/allergen details (in the 'details' attribute)\n"
            "- Image link (if available, formatted as 'IMAGE[url]')\n"
            "- Leave any field blank if the information is not present in the text.\n\n"
            "Guidelines:\n"
            "- Ignore unrelated data.\n"
            "- Do not fabricate information, such as image links or details not found in the text.\n"
            "- Ensure extracted data is accurate and formatted correctly.\n\n"
            "Here is the text chunk to analyze:\n{chunk}\n"
        )

        self.model = gpt_model
        self.response_model = SmallResponse

    def __call__(self, chunk: str) -> List[Dict[str, Any]]:
        prompt = self.prompt_template.format(chunk=chunk)
        try:
            response = client.beta.chat.completions.parse(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format=self.response_model,
            )
            return [item.dict() for item in response.choices[0].message.parsed.items]
        except Exception as e:
            print(f"Error processing chunk: {e}")
            return []

class ItemExpander:
    def __init__(self):
        self.prompt_template = (
            "Expand the following small-format menu item into a detailed large-format menu item. "
            "Include fields: menuType, itemType, foodCategoryId, flashcardBack, dietary, allergens, "
            "relatedIds, storeIds, shiftIds, and tagIds. The small-format menu item data is:\n\n"
            "Name: {name}\n"
            "Description: {description}\n"
            "Image: {image}\n"
            "Details: {details}\n\n"
            "Provide the expanded details in a structured format."
        )

        self.model = gpt_model
        self.response_model = LargeResponse  # Expect a structured LargeResponse

    def expand(self, small_item: MenuItemSmall) -> MenuItemLarge:
        prompt = self.prompt_template.format(
            name=small_item.name,
            description=small_item.description,
            image=small_item.image.dict(),
            details=", ".join(small_item.details) if small_item.details else "None",
        )
        try:
            response = client.beta.chat.completions.parse(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format=self.response_model,  # Parse as LargeResponse
            )

            # Debugging: print the raw response to check its structure
            print(f"Raw response: {response}")

            # Ensure the parsed response contains items
            parsed_response = response.choices[0].message.parsed
            if isinstance(parsed_response, LargeResponse) and parsed_response.items:
                return parsed_response.items[0]  # Return the first MenuItemLarge object
            else:
                print("Response is invalid or does not contain items.")
                return None
        except Exception as e:
            print(f"Error expanding item: {e}")
            return None



if __name__ == "__main__":
    # Sample test data
    test_small_item = MenuItemSmall(
        name="Pizza",
        description="A delicious flatbread topped with tomato sauce, cheese, and various toppings.",
        image=ImageData(file="path/to/image.jpg", filename="pizza.jpg"),
        details=["Vegetarian", "Customizable toppings"]
    )

    # Initialize the ItemExpander
    expander = ItemExpander()

    # Expand the sample small item
    print("Testing ItemExpander with sample data...")
    expanded_item = expander.expand(test_small_item)

    # Check and print the results
    if expanded_item:
        print("\nExpanded Item:")
        print(expanded_item.model_dump())  # Convert the Pydantic model to a dictionary for readable output
    else:
        print("\nFailed to expand the item.")
