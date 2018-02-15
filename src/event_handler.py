import boto3
import os


# noinspection PyUnusedLocal
def store_queued_events(event, context):
    sqs_client = boto3.client('sqs')
    queue_url = os.environ['QUEUE_URL']

    while True:
        message = __fetch_single_message(sqs_client, queue_url)
        if message is None:
            break

        print(message['Body'])


def __fetch_single_message(sqs_client, queue_url):
    response = sqs_client.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=1,
        VisibilityTimeout=300,  # 5 min timeout - any failed messages can be picked up by a later lambda
        WaitTimeSeconds=0,  # Don't wait for messages - if there aren't any left, then this lambda's job is done
    )
    return response['Messages'][0] if 'Messages' in response and response['Messages'] else None
