from typing import List, Dict, Any
from lib_types import InformedDeletionIndices, MenuItemLarge, MenuItemSmall, SmallResponse, LargeResponse
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
    running_category_list: List[str], 
    running_allergen_list: List[str], 
    running_dietary_list: List[str]
) -> List[Dict[str, Any]]:
    NAME_INSTR = "The name of the menu item as it appears in the content."
    DESCRIPTION_INSTR = "Extract the description VERBATIM as it appears in the content. If there is no provided description, then return 'NEEDS DESCRIPTION'"
    IMAGE_INSTR = "The image object has two fields, 'file' and 'fileName'. If a menu item's url is in the content, it should be stored in 'file' else 'file' should be PROMPT: prompt, where prompt is a natural language descriptor of what the menu item is. fileName should be something such as hamburger.jpg if the item was a hamburger."
    DETAILS_INSTR = "In details, store all extra information about an item as is found in the content."
    RUNNING_LIST_INSTR = "You are provided a list of menu item categories, allergen types, and dietary types found so far in other chunks. If you find new categories in this chunk, add them to the list. The goal is the standardize the categories, so do not repeat categories that are similar." # TODO: DID THIS WORK?

    prompt_template = (
        "The following text is scraped from a restaurant's website. Some of the content may include information about menu items, "
        "but most of it may not be relevant. Your task is to identify and extract details about the menu items from this text. "
        "If no menu data is found in the provided text, return an empty list. "
        "\n\n"
        f"You will be provided a chunk of text scraped from the content of a restaurant's website."
        f"Your task is to find information about this restaurant's menu items within the chunk."
        f"You will be provided a response tempplate. Here are the instructions for each field of the response:"
        f"'name:' {NAME_INSTR}"
        f"'description:' {DESCRIPTION_INSTR}"
        f"'image:' {IMAGE_INSTR}"
        f"'details:' {DETAILS_INSTR}"
        f"'running_category_list, running_allergen_list, running_dietary_list:' {RUNNING_LIST_INSTR}"
        f"Here are the lists, respectively: {running_category_list}, {running_allergen_list}, {running_dietary_list}\n"
        f"- Do NOT fabricate information, such as image links or details not found in the text."
        f"- Ensure extracted data is accurate and formatted correctly."
        "- Leave any field blank if the information is not present in the text.\n\n"
        "Guidelines:\n"
        "- Ignore unrelated data.\n"
        "- Do not fabricate information, such as image links or details not found in the text.\n"
        "- Ensure extracted data is accurate and formatted correctly.\n\n"
        "Here is the text chunk to analyze:\n{chunk}\n"
    )

    prompt = prompt_template.format(chunk=chunk)
    try:
        response = client.beta.chat.completions.parse(
            model=gpt_model,
            messages=[{"role": "user", "content": prompt}],
            response_format=SmallResponse,
        )
        return [item.dict() for item in response.choices[0].message.parsed.items], response.choices[0].message.parsed.running_category_list, response.choices[0].message.parsed.running_allergen_list, response.choices[0].message.parsed.running_dietary_list
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
