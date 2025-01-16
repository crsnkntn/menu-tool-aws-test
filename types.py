
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


class InformedDeletionIndices(BaseModel):
    keep_these: List[int]
