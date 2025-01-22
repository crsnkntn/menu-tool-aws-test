from response_handler import ResponseHandler
from json_to_xlsx import write_to_excel_from_json
from openai_functions import generate_items, expand_item
from lib_types import *
from crawler import Crawler
from process_text import process_pdf, chunk_text_data, extract_content_from_html
from lib_types import MenuItemSmall, MenuItemLarge
from openai_functions import *
import re
from tqdm import tqdm

output_file = "with_filtering.txt"

def test_chunking(url):
    url = url.strip()

    # Use regex to extract the core part of the link (e.g., 'example')
    match = re.search(r"(?:https?://)?(?:www\.)?([^/]+)", url)
    if match:
        core_link = match.group(1)
        url = f"https://www.{core_link}.com"
    else:
        return None

    crawler = Crawler(url)
    print(f"Crawling URL: {url}")
    crawler.crawl()

    pdf_links, relevant_links = crawler.get_results()

    print(f"Processing {len(pdf_links)} PDF links.")
    pdf_text = [process_pdf(link) for link, _ in pdf_links if link]
    webpage_text = [extract_content_from_html(html) for link, html in relevant_links]

    all_text = [s.replace("\n", " ") for s in webpage_text.extend(pdf_text)]

    chunks = chunk_text_data(all_text, chunk_size=1000)
    print(f"Created {len(chunks)} chunks from the processed text.")

    # Write chunks to a file
    with open(output_file, "w", encoding="utf-8") as file:
        for chunk in chunks:
            file.write(chunk + "\n\n")  # Separate chunks with newlines
        print(f"Chunks written to 'output_chunks.txt'.")

if __name__ == "__main__":
    url = "savasannarbor"
    #test_chunking(url)

    handler = ResponseHandler(url)

    response = handler.handle_request()

    print(response)

    write_to_excel_from_json(response['menu_items'], f"{url}.xlsx")
