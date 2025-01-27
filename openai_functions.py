from typing import List, Dict, Any
from lib_types import InformedDeletionIndices, MenuItemLarge, MenuItemSmall, SmallResponse, LargeResponse, ListOfStrings
from openai import OpenAI
from dotenv import load_dotenv
import os

# Create the client and set the model
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
gpt_model = "gpt-4o-mini"

def informed_deletion(
    uncleaned: List[str], 
    topic: str,
    strictness: str
) -> List[str]:
    # Construct the prompt for GPT to decide which indices to keep
    original = uncleaned
    uncleaned = [string[:30] for string in uncleaned]
    prompt_template = (
        "Here is a list of strings. I am interested in strings related to {topic}. Identify and return the indices of strings {strictness}ly related to this! Thank you."
        "The output should be a JSON object in the format provided, a list of strings in a json object:"
        "Strings:\n{strings}"
    )

    # Safely format strings by escaping problematic characters
    formatted_strings = "\n".join([f"{i}: {repr(s)}" for i, s in enumerate(uncleaned)])
    prompt = prompt_template.format(strings=formatted_strings, topic=topic, strictness=strictness)

    try:
        response = client.beta.chat.completions.parse(
            model=gpt_model,
            messages=[{"role": "user", "content": prompt}],
            response_format=InformedDeletionIndices,
        )

        kept_indices = response.choices[0].message.parsed.keep_these
        return [original[i] for i in kept_indices]

    except Exception as e:
        print(f"Error processing prompt: {e}")
        return []


def generate_items(
    chunk: str, 
    running_category_list: List[str]
) -> List[Dict[str, Any]]:
    NAME_INSTR = "Extract the name of the menu item exactly as it appears in the content."
    DESCRIPTION_INSTR = (
        "Extract the description verbatim as it appears in the content. If there is no description in the content, DO NOT MAKE ONE UP, return 'NEEDS DESCRIPTION' instead."
    )
    IMAGE_INSTR = (
        "The image object contains two fields: 'file' and 'fileName'.\n"
        "- 'file': If a menu item's URL is in the content, store it here. Otherwise, store a prompt describing the menu item in natural language.\n"
        "- 'fileName': Use a descriptive name like 'hamburger.jpg' for a hamburger."
    )
    DETAILS_INSTR = "Extract any additional information about the menu item as presented in the content and store it in 'details'."
    RUNNING_LIST_INSTR = (
        "You will be provided a list of menu item categories that have been discovered in previous chunks."
        "Menu categories are things such as Appetizers/Entrees/Wine etc. but have varied names based on the conventions used by the restaurant."
        "If you find categories in this chunk not currently in the list, add them."
        "If you find missing categories that should be a restaurant menu category, add them as well."
    )

    prompt_template = (
        "The following text is scraped from a restaurant's website and may include menu item information or irrelevant content.\n\n"
        "Your task is to identify and extract menu item details accurately from the provided text. If no menu data is found, return an empty list.\n\n"
        "### Instructions for Response Fields ###\n"
        f"- 'name': {NAME_INSTR}\n"
        f"- 'description': {DESCRIPTION_INSTR}\n"
        f"- 'image': {IMAGE_INSTR}\n"
        f"- 'details': {DETAILS_INSTR}\n"
        f"- Running Lists: {RUNNING_LIST_INSTR}\n"
        "The current list is:\n"
        f"- Menu Categories: {running_category_list}\n"
        "### Guidelines ###\n"
        "- Only include information explicitly present in the text.\n"
        "- Leave fields blank if no information is available.\n"
        "- Do not fabricate data (e.g., image URLs or details not found in the text).\n"
        "- Ensure accurate formatting of extracted data.\n"
        "- Ignore irrelevant data.\n\n"
        "Here is the text chunk to analyze:\n{chunk}\n"
    )

    prompt = prompt_template.format(chunk=chunk)
    try:
        response = client.beta.chat.completions.parse(
            model=gpt_model,
            messages=[{"role": "user", "content": prompt}],
            response_format=SmallResponse,
        )
        return [item.dict() for item in response.choices[0].message.parsed.items], response.choices[0].message.parsed.running_category_list
    except Exception as e:
        print(f"Error processing chunk: {e}")
        return []


#TODO: HAVE A SEPARATE WINE/BEER/SPIRITS PROMPT
def expand_item(
    small_item: MenuItemSmall, 
    categories: List[str], 
    allergens: List[str], 
    dietary: List[str]
) -> MenuItemLarge:
    NAME_INSTR = "Leave as is."
    DESCRIPTION_INSTR = "Leave as is. In the case of a wine/beer/spirit, the description should be the same as the flashcard back."
    IMAGE_INSTR = "Leave as is."
    MENUTYPE_INSTR = "Enter as 'Menu Item'"
    ITEMTYPE_INSTR = "Food or Beverage"
    FOODCATEGORYID_INSTR = f"Choose a category for this item from this list: {categories}"
    FLASHCARDBACK_INSTR = "This should be the same as the description. For only wines/beers/spirits include three bullet points that highlight its uniqueness such as notes, region, fun facts etc."
    ALLERGEN_INSTR = f"Choose allergens from this list that are in this menu item: {allergens}"
    DIETARY_INSTR = f"Choose dietary options that apply to this menu item: {dietary}"

    prompt_template = (
        "Expand the following small-format menu item into a detailed large-format menu item. "
        "Include fields: menuType, itemType, foodCategoryId, flashcardBack, dietary, allergens, "
        "relatedIds, storeIds, shiftIds, and tagIds. The small-format menu item data is:\n\n"
        f"You will be provided information about a menu item."
        f"Your task is to generate additional content for the menu item."
        f"Here are the instructions for each data field:"
        f"'name:' {NAME_INSTR}\n"
        f"'description:' {DESCRIPTION_INSTR}\n"
        f"'image:' {IMAGE_INSTR}\n"
        f"'menuType:' {MENUTYPE_INSTR}\n"
        f"'itemType:' {ITEMTYPE_INSTR}\n"
        f"'foodCategoryId:' {FOODCATEGORYID_INSTR}\n"
        f"'flashcardBack:' {FLASHCARDBACK_INSTR}\n"
        f"'allergenInfo:' {ALLERGEN_INSTR}\n"
        f"'dietaryInfo:' {DIETARY_INSTR}\n"
        f"Name: {small_item.name}\n"
        f"Description: {small_item.description}\n"
        f"Image: {small_item.image}\n"
        f"Details: {small_item.details}\n\n"
        f"Leave the relatedIds, storeIds, shiftIds, tagIds fields blank."
        "Provide the expanded details in a structured format."
    )

    prompt = prompt_template.format(
        name=small_item.name,
        description=small_item.description,
        image=small_item.image.dict(),
        details=", ".join(small_item.details) if small_item.details else "None",
    )
    try:
        response = client.beta.chat.completions.parse(
            model=gpt_model,
            messages=[{"role": "user", "content": prompt}],
            response_format=MenuItemLarge,
        )

        #print(f"Raw response: {response}")

        parsed_response = response.choices[0].message.parsed
        if isinstance(parsed_response, MenuItemLarge):
            return parsed_response
        else:
            print("Response is invalid or not of type MenuItemLarge.")
            return None
    except Exception as e:
        print(f"Error expanding item: {e}")
        return None



def standardize_categories(
    category_list: List[str]
):
    required_categories = ["Wines", "Cocktails", "Beers", "Spirits", "Appetizers", "Soups", "Starters", "Entrees"]
    prompt = f"You will be given a list of categories found on a restaurant's menu. If any of the following are missing from the list, add them: {required_categories}. Remember that there are mutliple words for a term, so dont duplicate categories. Here is the current list: {category_list}"
    
    try:
        response = client.beta.chat.completions.parse(
            model=gpt_model,
            messages=[{"role": "user", "content": prompt}],
            response_format=ListOfStrings,
        )

        parsed_response = response.choices[0].message.parsed
        if isinstance(parsed_response, ListOfStrings):
            return parsed_response.strings
        else:
            print("Response is invalid or not of type MenuItemLarge.")
            return None
    except Exception as e:
        print(f"Error expanding item: {e}")
        return None
