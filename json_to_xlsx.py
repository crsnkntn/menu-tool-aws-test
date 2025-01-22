import pandas as pd
from typing import List, Dict

# Example JSON data (list of dictionaries created by dumping MenuItemLarge objects)
menu_items_json = [
    {
        "name": "Spaghetti Bolognese",
        "description": "A classic Italian pasta dish with rich meat sauce.",
        "image": "https://example.com/images/spaghetti.jpg",
        "menuType": "Dinner",
        "itemType": "Main Course",
        "foodCategoryId": 1,
        "flashcardBack": "Rich and hearty Italian pasta.",
        "dietary": ["Gluten"],
        "allergens": ["Gluten"],
        "relatedIds": ["123", "456"],
        "storeIds": [1, 2],
        "shiftIds": [101, 102],
        "tagIds": ["italian", "pasta"]
    },
    {
        "name": "Caesar Salad",
        "description": "Crisp romaine lettuce with creamy Caesar dressing.",
        "image": "https://example.com/images/caesar.jpg",
        "menuType": "Lunch",
        "itemType": "Salad",
        "foodCategoryId": 2,
        "flashcardBack": "A refreshing salad with a tangy dressing.",
        "dietary": ["Vegetarian"],
        "allergens": ["Dairy"],
        "relatedIds": ["789"],
        "storeIds": [1],
        "shiftIds": [101],
        "tagIds": ["salad", "vegetarian"]
    }
]

# Convert JSON data to a DataFrame
def menu_items_json_to_dataframe(menu_items: List[Dict]) -> pd.DataFrame:
    data = [
        {
            "Name": item.get("name", ""),
            "Description": item.get("description", ""),
            "Image": item.get("image", ""),
            "Menu Type": item.get("menuType", ""),
            "Item Type": item.get("itemType", ""),
            "Food Category ID": item.get("foodCategoryId", ""),
            "Flashcard Back": item.get("flashcardBack", ""),
            "Dietary": ", ".join(item.get("dietary", [])),
            "Allergens": ", ".join(item.get("allergens", [])),
            "Related IDs": ", ".join(item.get("relatedIds", [])),
            "Store IDs": ", ".join(map(str, item.get("storeIds", []))),
            "Shift IDs": ", ".join(map(str, item.get("shiftIds", []))),
            "Tag IDs": ", ".join(item.get("tagIds", [])),
        }
        for item in menu_items
    ]
    return pd.DataFrame(data)

# Write the data to an Excel file
def write_to_excel_from_json(menu_items: List[Dict], filename: str):
    df = menu_items_json_to_dataframe(menu_items)
    df.to_excel(filename, index=False)
    print(f"Excel file '{filename}' created successfully.")
    