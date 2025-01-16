from typing import List, Dict, Any
from types import InformedDeletionIndices, MenuItemLarge, MenuItemSmall, SmallResponse, LargeResponse

gpt_model = "gpt-4o-mini"

def informed_deletion(
    client, 
    uncleaned: List[str], 
    topic: str,
    strictness: str
) -> List[str]:
    # Construct the prompt for GPT to decide which indices to keep
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
        return [uncleaned[i] for i in kept_indices]

    except Exception as e:
        print(f"Error processing prompt: {e}")
        return []


def generate_items(client, chunk: str) -> List[Dict[str, Any]]:
    prompt_template = (
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

    prompt = prompt_template.format(chunk=chunk)
    try:
        response = client.beta.chat.completions.parse(
            model=gpt_model,
            messages=[{"role": "user", "content": prompt}],
            response_format=SmallResponse,
        )
        return [item.dict() for item in response.choices[0].message.parsed.items]
    except Exception as e:
        print(f"Error processing chunk: {e}")
        return []


def expand_item(client, small_item: MenuItemSmall) -> MenuItemLarge:
    prompt_template = (
        "Expand the following small-format menu item into a detailed large-format menu item. "
        "Include fields: menuType, itemType, foodCategoryId, flashcardBack, dietary, allergens, "
        "relatedIds, storeIds, shiftIds, and tagIds. The small-format menu item data is:\n\n"
        "Name: {name}\n"
        "Description: {description}\n"
        "Image: {image}\n"
        "Details: {details}\n\n"
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
            response_format=LargeResponse,
        )

        print(f"Raw response: {response}")

        parsed_response = response.choices[0].message.parsed
        if isinstance(parsed_response, LargeResponse) and parsed_response.items:
            return parsed_response.items[0]  # Return the first MenuItemLarge object
        else:
            print("Response is invalid or does not contain items.")
            return None
    except Exception as e:
        print(f"Error expanding item: {e}")
        return None
