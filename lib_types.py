from pydantic import BaseModel
from typing import List

# Define models
class ImageData(BaseModel):
    file: str
    filename: str


class MenuItemSmall(BaseModel):
    name: str
    description: str
    image: ImageData
    details: List[str]


# Used as the response type for gpt
class SmallResponse(BaseModel):
    items: List[MenuItemSmall]
    running_category_list: List[str]
    running_allergen_list: List[str]
    running_dietary_list: List[str]


class MenuItemLarge(BaseModel):
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


class LargeResponse(BaseModel):
    items: List[MenuItemLarge]


class InformedDeletionIndices(BaseModel):
    keep_these: List[int]
