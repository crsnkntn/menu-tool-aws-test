from pypdf import PdfReader
import re
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from typing import List, Dict, Any
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from collections import deque
from source.nlp_functions import informed_deletion

# Set up Selenium WebDriver with Chrome
chrome_options = Options()
chrome_options.add_argument("--headless")  # Run in headless mode
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options) 
driver.set_page_load_timeout(30) 

# Compile regex patterns once
WHITESPACE_PATTERN = re.compile(r"\s+")
BASE64_PATTERN = re.compile(r"data:image/[a-zA-Z]+;base64,")
NON_ALPHA_PATTERN = re.compile(r"[a-zA-Z0-9\s]")


def process_pdf(pdf_url):
    print(f"Processing {pdf_url}")
    try:
        response = requests.get(pdf_url, timeout=30)
        response.raise_for_status()
        with open("temp.pdf", "wb") as temp_pdf:
            temp_pdf.write(response.content)
        
        reader = PdfReader("temp.pdf")
        return "".join(page.extract_text() for page in reader.pages)

    except Exception as e:
        print(f"Failed to fetch the pdf: {pdf_url}, exception {e}")


def clean_text(text: str) -> str:
    # Normalize whitespace
    cleaned_text = WHITESPACE_PATTERN.sub(" ", text).strip()

    # Filter out non-human-readable text
    stripped_text = text.strip()

    if len(stripped_text) > 500 and " " not in stripped_text:
        return ""

    if BASE64_PATTERN.match(stripped_text):
        return ""

    if len(NON_ALPHA_PATTERN.sub("", stripped_text)) / len(stripped_text) > 0.3:
        return ""

    return cleaned_text


def chunk_text_data(pdf_text_list, webpage_text_list, chunk_size):
    combined_text = pdf_text_list + webpage_text_list
    full_text = " ".join(combined_text)
    chunks = []

    # Create chunks of the specified size
    for start in range(0, len(full_text), chunk_size):
        chunk = full_text[start:start + chunk_size]
        chunks.append(chunk.strip())

    return chunks


def extract_menu_data(bs_parser, repetition_threshold=5):
    menu_data = []
    # Prevents nearby duplicates
    recent_lines = deque(maxlen=repetition_threshold)

    for tag in bs_parser.find_all(True):
        if tag.name == "img" and tag.has_attr("src"):
            line = f"IMAGE[{clean_text(tag['src'])}]"
        else:
            text = tag.text.strip()
            if not text:
                continue
            line = clean_text(text)

        if line and line not in recent_lines:
            menu_data.append(line)
            recent_lines.append(line)

    return menu_data


def filter_lines(lines: List[str], batch_size) -> List[str]:
    # Define in context since the lines object will be loaded nearby in memory
    def is_non_content(line: str) -> bool:
        snippet = line[:100].strip()  # Take the first 100 characters and strip whitespace

        # Rule 1: Check for excessive non-alphanumeric characters
        if len(re.sub(r"[a-zA-Z0-9\s]", "", snippet)) / max(len(snippet), 1) > 0.4:
            return True

        # Rule 2: Check for typical code patterns (e.g., HTML tags, base64, or random characters)
        if re.search(r"<[a-zA-Z]+.*?>", snippet):  # Detect HTML-like tags
            return True
        if re.match(r"data:image/[a-zA-Z]+;base64,", snippet):  # Detect base64 image data
            return True

        # Rule 3: Check for random-like text with no spaces
        if len(snippet) > 50 and " " not in snippet:
            return True

        # Rule 5: Detect JavaScript-like function definitions or object literals
        if re.match(r"^!function|^window\.\w+|^{\"|^\[", snippet):  # JS functions, window objects, JSON
            return True

        # Rule 6: Detect lines with excessive curly braces or square brackets
        if len(re.findall(r"[{}[\]]", snippet)) / max(len(snippet), 1) > 0.2:
            return True

        # Rule 7: Detect key-value patterns typical of JSON or configuration
        if re.search(r"\"[^\"]+\"\s*:\s*[^\s]+", snippet):
            return True

        return False

    # Filter the lines
    filtered_kinda = [line for line in lines if not is_non_content(line)]
    fully_filtered = []

    for i in range(0, len(filtered_kinda), batch_size):
        fully_filtered.extend(informed_deletion(filtered_kinda[i:i+batch_size], "restaurant menus, drinks menu, wine, beer", "even remote"))

    return fully_filtered


def extract_text_from_webpage(url: str, batch_size=50) -> List[str]:
    print(f"Starting extraction for URL: {url}")
    try:
        # Load the webpage
        print(f"Loading page: {url}")
        driver.get(url)
        print(f"Page loaded successfully: {url}")

        # Get the page source
        html = driver.page_source
        print(f"Page source retrieved for: {url}")

        # Parse the HTML content
        bs_parser = BeautifulSoup(html, "html.parser")
        print(f"HTML parsed for: {url}")

        # Remove unnecessary tags
        bs_parser.find_all(["script", "style", "meta", "link", "svg", "noscript"], recursive=True)
        print(f"Unnecessary tags removed for: {url}")

        # Extract menu data
        raw_lines = extract_menu_data(bs_parser)
        print(f"Raw lines extracted for {url}: {len(raw_lines)} lines")

        # Filter the lines
        filtered_lines = filter_lines(raw_lines, batch_size=batch_size)
        print(f"Filtered lines for {url}: {len(filtered_lines)} lines")

        return filtered_lines
    except Exception as e:
        print(f"Exception caught during extraction for {url}: {e}")
        return []


def process_urls(urls):
    print(f"Starting processing for {len(urls)} URLs.")
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(extract_text_from_webpage, url): url for url in urls}
        for future in futures:
            url = futures[future]
            try:
                print(f"Processing URL: {url}")
                result = future.result()
                results.extend(result)
                print(f"Finished processing URL: {url}. Extracted {len(result)} lines.")
            except Exception as e:
                print(f"Error processing URL {url}: {e}")

    # Remove empty strings
    results = [text for text in results if text]
    print(f"Finished processing all URLs. Total results: {len(results)} lines.")
    return results
