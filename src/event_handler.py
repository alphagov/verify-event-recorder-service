import boto3
import logging
import os

from src.database import create_db_connection, write_to_database
from src.decryption import decrypt_message
from src.event_mapper import event_from_json
from src.s3 import fetch_decryption_key
from src.sqs import fetch_single_message, delete_message
from src.kms import decrypt

logging.basicConfig(level=logging.INFO)


# noinspection PyUnusedLocal
def store_queued_events(_, __):
    sqs_client = boto3.client('sqs')
    queue_url = os.environ['QUEUE_URL']
    db_connection = create_db_connection()
    encrypted_decryption_key = fetch_decryption_key()
    decryption_key = decrypt(encrypted_decryption_key)

    while True:
        message = fetch_single_message(sqs_client, queue_url)
        if message is None:
            break

        # noinspection PyBroadException
        # catch all errors and log them - we never want a single failing message to kill the process.
        try:
            decrypted_message = decrypt_message(message['Body'], decryption_key)
            event = event_from_json(decrypted_message)
            write_to_database(event, db_connection)
            delete_message(sqs_client, queue_url, message)
        except Exception as exception:
            logging.getLogger('event-recorder').exception('Failed to store message')
