import boto3
import os
import json

from src.db_helper import RunInTransaction, create_db_connection
from src.event_mapper import event_from_json


# noinspection PyUnusedLocal
def store_queued_events(_, __):
    sqs_client = boto3.client('sqs')
    queue_url = os.environ['QUEUE_URL']
    db_connection = create_db_connection()

    while True:
        message = __fetch_single_message(sqs_client, queue_url)
        if message is None:
            break

        # noinspection PyBroadException
        # catch all errors and log them - we never want a single failing message to kill the process.
        try:
            event = event_from_json(message['Body'])
            __write_to_database(event, db_connection)
            __delete_message(sqs_client, queue_url, message)
        except Exception as exception:
            print('Failed to store message - Exception: {0}'.format(str(exception)))


def __fetch_single_message(sqs_client, queue_url):
    response = sqs_client.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=1,
        VisibilityTimeout=300,  # 5 min timeout - any failed messages can be picked up by a later lambda
        WaitTimeSeconds=0,  # Don't wait for messages - if there aren't any left, then this lambda's job is done
    )
    return response['Messages'][0] if 'Messages' in response and response['Messages'] else None


def __write_to_database(event, db_connection):
    with RunInTransaction(db_connection) as cursor:
        cursor.execute("""
            INSERT INTO events
            (event_id, event_type, timestamp, details)
            VALUES
            ('%s', '%s', '%s', '%s');
        """ % (
            event.event_id,
            event.event_type,
            event.timestamp,
            json.dumps(event.details)
        ))


def __delete_message(sqs_client, queue_url, message):
    sqs_client.delete_message(
        QueueUrl=queue_url,
        ReceiptHandle=message['ReceiptHandle']
    )
