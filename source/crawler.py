from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from source.nlp_functions import informed_deletion

import time



class Crawler:
    def __init__(self, base_url, max_depth=3, max_threads=5):
        self.base_url = base_url
        self.max_depth = max_depth
        self.visited = {}
        self.all_links = set()
        self.lock = Lock()  # Protect shared resources
        self.max_threads = max_threads

    def create_driver(self):
        """Set up a new Selenium WebDriver instance."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        return webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )

    def fetch_web_page(self, url):
        """Fetch and render a web page using Selenium."""
        driver = self.create_driver()  # Create a new driver instance for this thread
        try:
            print(f"Fetching: {url}")
            driver.get(url)

            # Scroll to load dynamic content
            for _ in range(3):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)

            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.TAG_NAME, "a"))
            )
            return driver.page_source
        except Exception as e:
            print(f"Error fetching the URL {url}: {e}")
            return None
        finally:
            driver.quit()  # Close the WebDriver instance

    def extract_links(self, base_url, html_content):
        """Extract all links from the given HTML content."""
        soup = BeautifulSoup(html_content, 'html.parser')
        links = set()
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            full_url = urljoin(base_url, href)
            links.add(full_url)
        return links

    def crawl_page(self, url, depth):
        """Crawl a single page and extract links."""
        if url in self.visited and self.visited[url] <= depth:
            return

        if depth > self.max_depth:
            return

        with self.lock:  # Protect shared resource
            self.visited[url] = depth

        html_content = self.fetch_web_page(url)
        if html_content is None:
            return

        links = self.extract_links(url, html_content)

        with self.lock:  # Protect shared resource
            self.all_links.update(links)

        return [(link, depth + 1) for link in links if urlparse(link).netloc == urlparse(self.base_url).netloc]

    def crawl(self):
        """Crawl the website using multithreading."""
        to_crawl = [(self.base_url, 0)]
        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            while to_crawl:
                futures = {executor.submit(self.crawl_page, url, depth): (url, depth) for url, depth in to_crawl}
                to_crawl = []  # Reset for the next iteration

                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        to_crawl.extend(result)

    def get_links(self):
        """Categorize and return all links, PDF links, and relevant links."""
        pdf_links = [link for link in self.all_links if link.lower().endswith('.pdf')]
        relevant_links = informed_deletion(
            list(self.all_links),
            f"links that may contain restaurant menu information for {self.base_url}",
            "certain"
        )
        return self.all_links, pdf_links, relevant_links

    def close(self):
        """Close the Selenium WebDriver."""
        self.driver.quit()


# Example usage
if __name__ == "__main__":
    base_url = "https://bigboy.com"
    crawler = Crawler(base_url)
    crawler.crawl()
    all_links, pdf_links, relevant_links = crawler.get_links()

    print(f"All Links: {all_links}")
    print(f"PDF Links: {len(pdf_links)}")
    print(f"Relevant Links: {len(relevant_links)}")

    crawler.close()
