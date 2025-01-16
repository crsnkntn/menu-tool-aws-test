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


class Crawler:
    def __init__(self, start_url, max_depth=3):
        self.start_url = start_url
        self.max_depth = max_depth
        self.visited = {}
        self.relevant_links = set()
        self.pdf_links = set()

        load_dotenv()

        print(f"Initialized Crawler with start_url: {start_url} and max_depth: {max_depth}")

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
        driver = self.create_driver()
        try:
            driver.get(url)
            print(f"Successfully fetched: {url}")

            # Scroll to load dynamic content
            for i in range(2):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                print(f"Scroll {i + 1} completed for: {url}")
                time.sleep(1)

            WebDriverWait(driver, 8).until(
                EC.presence_of_all_elements_located((By.TAG_NAME, "a"))
            )
            print(f"Page content loaded for: {url}")
            return driver.page_source
        except Exception as e:
            print(f"Error fetching the URL {url}: {e}")
            return None
        finally:
            driver.quit()

    def extract_links(self, current_url, html_content):
        """Extract all links from the given HTML content."""
        print(f"Extracting links from: {current_url}")
        # Ensure `current_url` has a trailing slash if it is not a file path
        if not current_url.endswith("/") and "/" not in current_url.split("/")[-1]:
            current_url += "/"
            print(f"Normalized current_url: {current_url}")

        soup = BeautifulSoup(html_content, 'html.parser')
        links = set()
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if not href or href.startswith("#"):  # Skip empty or fragment-only links
                continue
            if not href.startswith("http"):  # Resolve relative links
                full_url = urljoin(current_url, href)
            else:
                full_url = href
            print(f"Found href: {href} -> Resolved to: {full_url}")
            links.add(full_url)
        print(f"Total links extracted from {current_url}: {len(links)}")
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
        print(f"Crawling page: {url} at depth: {depth}")
        if url in self.visited and self.visited[url] <= depth:
            print(f"Skipping already visited URL: {url} at depth: {depth}")
            return

        if depth > self.max_depth:
            print(f"Maximum depth exceeded for URL: {url}")
            return

        self.visited[url] = depth
        html_content = self.fetch_web_page(url)
        if html_content is None:
            print(f"No content fetched for URL: {url}")
            return

        links = self.extract_links(url, html_content)

        # Identify PDF links
        pdf_links = {
            link for link in links
            if link.lower().endswith('.pdf') and "application/pdf" in self.get_content_type(link)
        }
        self.pdf_links.update(pdf_links)
        print(f"PDF links found on {url}: {len(pdf_links)}")

        # Identify relevant links
        relevant_links = informed_deletion(
            list(links),
            f"links that may contain restaurant menu information for {self.start_url}",
            "certain"
        )
        self.relevant_links.update(relevant_links)
        print(f"Relevant links found on {url}: {len(relevant_links)}")

        for link in relevant_links:
            if urlparse(link).netloc == urlparse(self.start_url).netloc:
                print(f"Recursively crawling relevant link: {link}")
                self.crawl_page(link, depth + 1)

    def crawl(self):
        """Start crawling from the start URL."""
        print(f"Starting crawl from: {self.start_url}")
        self.crawl_page(self.start_url, 0)
        print("Crawl completed.")

    def get_results(self):
        """Return all visited links, relevant links, and PDF links."""
        print("Fetching crawl results.")
        return self.visited, list(self.relevant_links), list(self.pdf_links)


# Example usage
if __name__ == "__main__":
    start_url = "https://bigboy.com"
    crawler = Crawler(start_url)
    crawler.crawl()
    visited_links, relevant_links, pdf_links = crawler.get_results()

    print(f"Visited Links: {len(visited_links)}")
    print(f"Relevant Links: {len(relevant_links)}")
    print(f"PDF Links: {len(pdf_links)}")
