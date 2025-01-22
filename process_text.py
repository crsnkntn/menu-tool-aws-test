from pypdf import PdfReader
import re
import time
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
from openai_functions import informed_deletion

# Set up Selenium WebDriver with Chrome
chrome_options = Options()
chrome_options.add_argument("--headless")  # Run in headless mode
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options) 
driver.set_page_load_timeout(30) 

# Compile regex patterns for clean_text function
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


def filter_lines(lines: List[str], batch_size=50) -> List[str]:
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

    filtered_kinda = [line for line in lines if not is_non_content(line)]
    fully_filtered = []

    for i in range(0, len(filtered_kinda), batch_size):
        fully_filtered.extend(informed_deletion(filtered_kinda[i:i+batch_size], "human-readable content related to a restaurants menu items", "certain"))

    fully_filtered = [s.replace('\n', ' ') for s in fully_filtered]
    return fully_filtered


def extract_content_from_html(html: str, repetition_threshold=5) -> List[str]:
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

    bs_parser = BeautifulSoup(html, "html.parser")

    # Remove tags that contain code and irrelevant stuff
    for tag in bs_parser.find_all(["script", "style", "meta", "link", "svg", "noscript"], recursive=True):
        tag.decompose()

    # Extract anything that may contain image or text content
    raw_lines = []
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
            raw_lines.append(line)
            recent_lines.append(line)

    # Filter the content
    filtered_lines = filter_lines(raw_lines)

    return filtered_lines


def chunk_text_data(text_list, chunk_size, buffer_size=100):
    if not test_list:
        return []

    full_text = " ".join(test_list)

    sentences = re.split(r'(?<=[.!?]) +', full_text)
    chunks, current_chunk = [], []

    for sentence in sentences:
        if len(" ".join(current_chunk) + sentence) > chunk_size:
            chunk = " ".join(current_chunk).strip()
            chunks.append(chunk)

            buffer_start = max(0, len(chunk) - buffer_size)
            buffer_text = chunk[buffer_start:]

            current_chunk = [buffer_text]
        current_chunk.append(sentence)

    if current_chunk:
        chunks.append(" ".join(current_chunk).strip())

    return chunks
