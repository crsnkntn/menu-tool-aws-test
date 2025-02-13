from pydantic import BaseModel
from typing import List

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

class PartialItemList(BaseModel):
    items: List[PartialItem]

class FullItemList(BaseModel):
    items: List[FullItem]

class ListOfInt(BaseModel):
    elements: List[int]

class ListOfStrings(BaseModel):
    elements: List[str]
