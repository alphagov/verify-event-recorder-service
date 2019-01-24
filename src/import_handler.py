import logging
import os
import json

from src.database import create_db_connection, write_audit_event_to_database, \
    write_billing_event_to_database, write_fraud_event_to_database
from src.event_mapper import event_from_json_object
from src.s3 import fetch_import_file, delete_import_file
from src.kms import decrypt

logging.basicConfig(level=logging.INFO)


def import_events(event, __):
    database_password = None
    if 'ENCRYPTED_DATABASE_PASSWORD' in os.environ:
        database_password = decrypt(os.environ['ENCRYPTED_DATABASE_PASSWORD']).decode()
    db_connection = create_db_connection(database_password)
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        filename = record['s3']['object']['key']

        iterable = fetch_import_file(bucket, filename)

        for line in iterable:
            try:
                message_envelope = json.loads(line)
                event = event_from_json_object(message_envelope['document'])

                write_audit_event_to_database(event, db_connection)
                if event.event_type == 'session_event' and event.details.get('session_event_type') == 'idp_authn_succeeded':
                    write_billing_event_to_database(event, db_connection)
                if event.event_type == 'session_event' and event.details.get('session_event_type') == 'fraud_detected':
                    write_fraud_event_to_database(event, db_connection)

            except Exception as exception:
                logging.getLogger('event-recorder').exception('Failed to store message{}'.format(exception))

        delete_import_file(bucket, filename)
