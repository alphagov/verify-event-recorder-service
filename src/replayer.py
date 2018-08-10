import boto3
import logging
import os

from src.sqs import fetch_single_message, delete_message, send_message

logging.basicConfig(level=logging.INFO)


def replay_dead_letter_events(_, __):
    sqs_client = boto3.client('sqs')
    destination_queue = os.environ['QUEUE_URL']
    source_queue = "{}-dead-letter-queue".format(destination_queue)

    while True:
        message = fetch_single_message(sqs_client, source_queue)
        if message is None:
            break

        try:
            send_message(sqs_client, destination_queue, message)
            delete_message(sqs_client, source_queue, message)
        except Exception as exception:
            logging.getLogger('event-recorder').exception('Failed to replay message')
