from openai_functions import generate_items, expand_item
from lib_types import *
from crawler import Crawler
from process_text import process_pdf, chunk_text_data, extract_content_from_html
from lib_types import MenuItemSmall, MenuItemLarge
from generate_menu_handler import GenerateMenuHandler
from openai_functions import *
import re
from tqdm import tqdm

if __name__ == "__main__":
    url = "eatathazels"
    
    handler = GenerateMenuHandler(url)

    response = handler.run()

    print(response)

    write_to_excel_from_json(response['menu_items'], f"{url}.xlsx")
