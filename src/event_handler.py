import logging
import os

import boto3

from src.common import get_database_password
from src.database import create_db_connection, write_audit_event_to_database, \
    write_billing_event_to_database, write_fraud_event_to_database
from src.decryption import decrypt_message
from src.event_mapper import event_from_json
from src.kms import decrypt
from src.s3 import fetch_decryption_key
from src.sqs import fetch_single_message, delete_message


# noinspection PyUnusedLocal
def store_queued_events(_, __):
    sqs_client = boto3.client('sqs')
    queue_url = os.environ['QUEUE_URL']

    logger = logging.getLogger('event-recorder')
    logger.setLevel(logging.INFO)

    if 'ENCRYPTION_KEY' in os.environ:
        encrypted_decryption_key = os.environ['ENCRYPTION_KEY']
        logger.info('Got decryption key from environment variable')
    else:
        encrypted_decryption_key = fetch_decryption_key()
        logger.info('Got decryption key from S3')
    decryption_key = decrypt(encrypted_decryption_key)
    logger.info('Decrypted key successfully')

    dsn = os.environ['DB_CONNECTION_STRING']

    db_connection = create_db_connection(dsn, get_database_password(dsn))
    logger.info('Created connection to DB')

    event_count = 0
    while True:
        message = fetch_single_message(sqs_client, queue_url)
        if message is None:
            logger.info('Queue is empty - finishing after {0} events'.format(event_count))
            break

        event_count += 1

        # noinspection PyBroadException
        # catch all errors and log them - we never want a single failing message to kill the process.
        event = None
        try:
            decrypted_message = decrypt_message(message['Body'], decryption_key)
            event = event_from_json(decrypted_message)
            logger.info('Decrypted event with ID: {0}'.format(event.event_id))
            write_audit_event_to_database(event, db_connection)
            logger.info('Stored audit event: {0}'.format(event.event_id))
            if event.event_type == 'session_event' and event.details.get('session_event_type') == 'idp_authn_succeeded':
                write_billing_event_to_database(event, db_connection)
                logger.info('Stored billing event: {0}'.format(event.event_id))
            if event.event_type == 'session_event' and event.details.get('session_event_type') == 'fraud_detected':
                write_fraud_event_to_database(event, db_connection)
                logger.info('Stored fraud event: {0}'.format(event.event_id))
            delete_message(sqs_client, queue_url, message)
            logger.info('Deleted event from queue with ID: {0}'.format(event.event_id))
        except Exception:
            if event:
                logger.exception(
                    'Failed to store event {0}, event type "{1}" from SQS message ID {2}'.format(event.event_id,
                                                                                                 event.event_type,
                                                                                                 message['MessageId']))
            else:
                logger.exception('Failed to decrypt message, SQS ID = {0}'.format(message['MessageId']))
