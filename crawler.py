import time
import re
import os
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
        self.core_link = re.search(r"(?:https?://)?(?:www\.)?([^/]+)", self.start_url).group(1)
        self.max_depth = max_depth
        self.visited = set()  # Use a set to track visited URLs
        self.relevant_links = set()  # Now stores (link, content) tuples
        self.pdf_links = set()  # Now stores (link, content) tuples
        self.driver = self.create_driver()

    def __del__(self):
        self.driver.quit()

    def create_driver(self):
        """Setup Selenium WebDriver with Headless Chrome."""
        print("🔧 Initializing Selenium WebDriver...")

        # Define paths for Chrome and ChromeDriver
        chromium_path = "/usr/bin/google-chrome"  # Use the standard system-installed Chrome path
        driver_path = "/usr/local/bin/chromedriver"  # Standard location for ChromeDriver

        # Set Chrome options
        chrome_options = Options()
        chrome_options.binary_location = chromium_path
        chrome_options.add_argument("--headless")  # Run in headless mode
        chrome_options.add_argument("--no-sandbox")  # Required for AWS Lambda/EC2
        chrome_options.add_argument("--disable-dev-shm-usage")  # Avoid shared memory issues
        chrome_options.add_argument("--disable-gpu")  # Disable GPU hardware acceleration
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")  # Reduce bot detection
        chrome_options.add_argument("--disable-infobars")  # Remove the Chrome info bar

        print(f"✅ Launching WebDriver with Chrome at {chromium_path} and Driver at {driver_path}")

        # Initialize and return the WebDriver
        return webdriver.Chrome(service=Service(driver_path), options=chrome_options)

    def scroll_until_loaded(self, timeout=10):
        """Scrolls the page until no new content is loaded."""
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        start_time = time.time()

        while True:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)  # Allow time for new content to load
            new_height = self.driver.execute_script("return document.body.scrollHeight")

            if new_height == last_height or (time.time() - start_time) > timeout:
                break
            last_height = new_height

    def wait_for_elements(self, timeout=10):
        """Wait until all elements are fully loaded."""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_all_elements_located((By.XPATH, "//*"))
            )
        except Exception as e:
            print(f"Error waiting for elements: {e}")

    def extract_iframe_content(self):
        """Extract content from all iframes on the page."""
        iframe_contents = []

        # Find all iframe elements
        iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
        print(f"Found {len(iframes)} iframes on the page.")

        for index, iframe in enumerate(iframes):
            try:
                # Switch to iframe context
                self.driver.switch_to.frame(iframe)
                print(f"Switched to iframe #{index + 1}")

                # Extract iframe content
                iframe_content = self.driver.page_source
                iframe_contents.append(iframe_content)
            except Exception as e:
                print(f"Error accessing iframe #{index + 1}: {e}")
            finally:
                # Switch back to the main content
                self.driver.switch_to.default_content()

        return iframe_contents

    def make_hidden_elements_visible(self):
        """Make hidden elements visible."""
        try:
            self.driver.execute_script("""
                let elements = document.querySelectorAll('[style*="display: none"]');
                for (let el of elements) {
                    el.style.display = 'block';
                }
            """)
        except Exception as e:
            print(f"Error making hidden elements visible: {e}")

    def extract_shadow_dom_content(self, shadow_host_selector):
        """Extract content from a Shadow DOM."""
        try:
            shadow_host = self.driver.find_element(By.CSS_SELECTOR, shadow_host_selector)
            shadow_root = self.driver.execute_script("return arguments[0].shadowRoot", shadow_host)
            return shadow_root.get_attribute('innerHTML')
        except Exception as e:
            print(f"Error extracting Shadow DOM content: {e}")
            return ""

    def fetch_web_page(self, url):
        """Fetch and render a web page using Selenium."""
        print(f"Attempting to fetch: {url}")
        try:
            self.driver.get(url)
            # Increase load time and scroll dynamically
            self.scroll_until_loaded()

            # Wait for all elements to load
            self.wait_for_elements()

            # Handle lazy loading by scrolling to elements
            lazy_elements = self.driver.find_elements(By.CSS_SELECTOR, ".lazy-load")
            for element in lazy_elements:
                self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                time.sleep(1)

            # Make hidden elements visible
            self.make_hidden_elements_visible()

            # Extract content from iFrames
            iframe_contents = self.extract_iframe_content()

            # Capture the main page source
            main_page_content = self.driver.page_source

            # Merge iframe content with main page content
            all_content = main_page_content + "\n".join(iframe_contents)

            print(f"Successfully fetched: {url}")
            return all_content
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

    def crawl_page(self, url):
        """Crawl a single page and extract relevant links and PDFs."""
        if url in self.visited:
            return

        self.visited.add(url)
        html_content = self.fetch_web_page(url)
        self.relevant_links.add((url, html_content))

        if html_content is None:
            print(f"No html content was found for {url}")
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
        relevant_links = [link for link in list(links) if "menu" in link and self.core_link in link]

        for link in relevant_links:
            if urlparse(link).netloc == urlparse(self.start_url).netloc:
                self.crawl_page(link)

    def crawl(self):
        """Start crawling from the start URL."""
        self.crawl_page(self.start_url)

        return self.get_results()

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
