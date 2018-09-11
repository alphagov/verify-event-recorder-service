import logging
import os

import boto3

from src.database import create_db_connection, write_audit_event_to_audit_database, \
    write_billing_event_to_billing_database, write_fraud_event_to_billing_database
from src.decryption import decrypt_message
from src.event_mapper import event_from_json
from src.kms import decrypt
from src.s3 import fetch_decryption_key
from src.sqs import fetch_single_message, delete_message

logging.basicConfig(level=logging.INFO)

# noinspection PyUnusedLocal
def store_queued_events(_, __):
    sqs_client = boto3.client('sqs')
    queue_url = os.environ['QUEUE_URL']

    if 'ENCRYPTION_KEY' in os.environ:
      encrypted_decryption_key = os.environ['ENCRYPTION_KEY']
    else:
      encrypted_decryption_key = fetch_decryption_key()
    decryption_key = decrypt(encrypted_decryption_key)

    database_password = None
    if 'ENCRYPTED_DATABASE_PASSWORD' in os.environ:
      database_password = decrypt(os.environ['ENCRYPTED_DATABASE_PASSWORD'])
    db_connection = create_db_connection(database_password)

    while True:
        message = fetch_single_message(sqs_client, queue_url)
        if message is None:
            break

        # noinspection PyBroadException
        # catch all errors and log them - we never want a single failing message to kill the process.
        try:
            decrypted_message = decrypt_message(message['Body'], decryption_key)
            event = event_from_json(decrypted_message)
            write_audit_event_to_audit_database(event, db_connection)
            if event.event_type == 'session_event' and 'session_event_type' in event.details and event.details['session_event_type'] == 'idp_authn_succeeded':
                write_billing_event_to_billing_database(event, db_connection)
            if event.event_type == 'session_event' and 'session_event_type' in event.details and event.details['session_event_type'] == 'fraud_detected':
                write_fraud_event_to_billing_database(event, db_connection)
            delete_message(sqs_client, queue_url, message)
        except Exception as exception:
            logging.getLogger('event-recorder').exception('Failed to store message')
