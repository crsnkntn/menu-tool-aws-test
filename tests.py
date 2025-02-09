from crawler import Crawler
from openai_functions import generate_items, informed_deletion, expand_item, standardize_categories


def save_request_to_s3(request_id, data):
    """Save a request object to S3."""
    try:
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=f"requests/{request_id}.json",
            Body=json.dumps(data),
            ContentType="application/json",
        )
    except ClientError as e:
        raise Exception(f"Error saving to S3: {e}")

if __name__ == "__main__":
    print("Testing the Crawler")
    crawler = Crawler("https://eatathazels.com")

    links, pdf_links = crawler.crawl()

    print("Crawling was a success, here is what was found:")
    for link, content in links:
        print(f"{len(content)}:{link}")
    for pdf_link in pdf_links:
        print(f"PDF: {pdf_link}")
