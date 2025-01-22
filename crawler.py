import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from openai_functions import informed_deletion
from process_text import process_pdf

class Crawler:
    def __init__(self, start_url, max_depth=3):
        self.start_url = start_url
        self.max_depth = max_depth
        self.visited = {}
        self.relevant_links = set()  # Now stores (link, content) tuples
        self.pdf_links = set()  # Now stores (link, content) tuples
        self.driver = self.create_driver()

        print(f"Initialized Crawler with start_url: {start_url} and max_depth: {max_depth}")

    def __del__(self):
        self.driver.quit()

    def create_driver(self):
        """Set up a new Selenium WebDriver instance."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        print("Creating a new Selenium WebDriver instance.")
        return webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )

    def fetch_web_page(self, url):
        """Fetch and render a web page using Selenium."""
        print(f"Attempting to fetch: {url}")
        try:
            self.driver.get(url)
            print(f"Successfully fetched: {url}")

            # Scroll to load dynamic content
            for i in range(2):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)

            WebDriverWait(self.driver, 8).until(
                EC.presence_of_all_elements_located((By.TAG_NAME, "a"))
            )
            return self.driver.page_source
        except Exception as e:
            print(f"Error fetching the URL {url}: {e}")
            return None

    def extract_links(self, current_url, html_content):
        """Extract all links from the given HTML content."""
        print(f"Extracting links from: {current_url}")
        soup = BeautifulSoup(html_content, 'html.parser')
        links = set()
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if not href or href.startswith("#"):  # Skip empty or fragment-only links
                continue
            try:
                full_url = urljoin(current_url, href)
                links.add(full_url)
            except Exception as e:
                print(f"Error resolving link {href}: {e}")
        
        return links

    def get_content_type(self, url):
        """Fetch the content type of a URL."""
        try:
            response = requests.head(url, allow_redirects=True, timeout=5)
            return response.headers.get("Content-Type", "")
        except requests.RequestException as e:
            print(f"Error fetching content type for {url}: {e}")
            return ""

    def crawl_page(self, url, depth):
        """Crawl a single page and extract relevant links and PDFs."""
        if url in self.visited:
            return

        if depth > self.max_depth:
            return

        self.visited[url] = depth
        html_content = self.fetch_web_page(url)
        if html_content is None:
            return

        links = self.extract_links(url, html_content)

        # Identify PDF links
        pdf_links = {
            link for link in links
            if link.lower().endswith('.pdf') and "application/pdf" in self.get_content_type(link)
        }
        for pdf_link in pdf_links:
            self.pdf_links.add((pdf_link, None)) 

        print(f"PDF links found on {url}: {len(pdf_links)}")

        # Identify relevant links
        relevant_links = informed_deletion(
            list(links),
            f"links that will contain information about this restaurant's menu items: {self.start_url}",
            "certain"
        )
        for relevant_link in relevant_links:
            if relevant_link not in self.visited:
                self.relevant_links.add((relevant_link, html_content))  # Pair link with content

        for link in relevant_links:
            if urlparse(link).netloc == urlparse(self.start_url).netloc:
                self.crawl_page(link, depth + 1)

    def crawl(self):
        """Start crawling from the start URL."""
        self.crawl_page(self.start_url, 0)

    def get_results(self):
        """Return relevant links and PDF links as (link, content) pairs."""
        return list(self.relevant_links), list(self.pdf_links)


# Example usage
if __name__ == "__main__":
    start_url = "https://bigboy.com"
    crawler = Crawler(start_url)
    crawler.crawl()
    visited_links, relevant_links, pdf_links = crawler.get_results()

    print(f"Visited Links: {len(visited_links)}")
    print(f"Relevant Links: {len(relevant_links)}")
    print(f"PDF Links: {len(pdf_links)}")
