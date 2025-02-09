import json
import boto3
import time
from generate_menu_handler import GenerateMenuHandler

sqs = boto3.client('sqs', region_name="us-east-2")
QUEUE_URL = "https://sqs.us-east-2.amazonaws.com/872515259264/menu-tool-queue"
s3 = boto3.client('s3', region_name="us-east-2")


def process_message(message):
    try:
        message_body = json.loads(message['Body'])
        url = message_body["url"]
        request_id = message_body["requestId"]

        print(f"Processing request {request_id} for URL: {url}")

        # Run menu generation (which internally interacts with S3)
        gen_handler = GenerateMenuHandler(url, request_id)
        gen_handler.run()

        print(f"Successfully processed request {request_id}")

    except Exception as e:
        print(f"Error processing request {request_id}: {str(e)}")


# Check for messages in the queue
def poll_sqs():
    while True:
        print("Checking for a message")
        response = sqs.receive_message(
            QueueUrl=QUEUE_URL,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=5
        )

        messages = response.get('Messages', [])
        for message in messages:
            print("Recieved a message")
            process_message(message)

            # Remove the message from the queue once processed
            sqs.delete_message(
                QueueUrl=QUEUE_URL,
                ReceiptHandle=message['ReceiptHandle']
            )
            print(f"Deleted message {message['MessageId']}")

        time.sleep(2)

if __name__ == "__main__":
    poll_sqs()
