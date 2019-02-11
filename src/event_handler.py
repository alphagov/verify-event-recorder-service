import logging
import os

import boto3

from src.database import create_db_connection, write_audit_event_to_database, \
    write_billing_event_to_database, write_fraud_event_to_database
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
      logging.getLogger('event-recorder').info('Got decryption key from envrionment variable')
    else:
      encrypted_decryption_key = fetch_decryption_key()
      logging.getLogger('event-recorder').info('Got decryption key from S3')
    decryption_key = decrypt(encrypted_decryption_key)
    logging.getLogger('event-recorder').info('Decrypted key successfully')

    database_password = None
    if 'ENCRYPTED_DATABASE_PASSWORD' in os.environ:
      # boto returns decrypted as b'bytes' so decode to convert to password string
      database_password = decrypt(os.environ['ENCRYPTED_DATABASE_PASSWORD']).decode()
    db_connection = create_db_connection(database_password)
    logging.getLogger('event-recorder').info('Created connection to DB')

    event_count = 0
    while True:
        event_count += 1
        message = fetch_single_message(sqs_client, queue_url)
        if message is None:
            logging.getLogger('event-recorder').info('Queue is empty - finishing after {0} events'.format(event_count))
            break

        # noinspection PyBroadException
        # catch all errors and log them - we never want a single failing message to kill the process.
        try:
            decrypted_message = decrypt_message(message['Body'], decryption_key)
            logging.getLogger('event-recorder').info('Decrypted event with ID: {0}'.format(event.event_id))
            event = event_from_json(decrypted_message)
            write_audit_event_to_database(event, db_connection)
            logging.getLogger('event-recorder').info('Stored audit event: {0}'.format(event.event_id))
            if event.event_type == 'session_event' and event.details.get('session_event_type') == 'idp_authn_succeeded':
                logging.getLogger('event-recorder').info('Stored billing event: {0}'.format(event.event_id))
                write_billing_event_to_database(event, db_connection)
            if event.event_type == 'session_event' and event.details.get('session_event_type') == 'fraud_detected':
                logging.getLogger('event-recorder').info('Stored fraud event: {0}'.format(event.event_id))
                write_fraud_event_to_database(event, db_connection)
            delete_message(sqs_client, queue_url, message)
            logging.getLogger('event-recorder').info('Deleted event from queue with ID: {0}'.format(event.event_id))
        except Exception as exception:
            logging.getLogger('event-recorder').exception('Failed to store message')
