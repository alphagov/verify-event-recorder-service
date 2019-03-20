import logging
import os
import json
import boto3

from src.database import create_db_connection, write_audit_event_to_database, \
    write_billing_event_to_database, write_fraud_event_to_database
from src.event_mapper import event_from_json_object
from src.s3 import fetch_import_file, delete_import_file
from src.kms import decrypt
from psycopg2.extensions import parse_dsn


def import_events(event, __):
    logger = logging.getLogger('event-recorder')
    logger.setLevel(logging.INFO)

    dsn = os.environ['DB_CONNECTION_STRING']

    database_password = None
    if 'ENCRYPTED_DATABASE_PASSWORD' in os.environ:
        # boto returns decrypted as b'bytes' so decode to convert to password string
        database_password = decrypt(os.environ['ENCRYPTED_DATABASE_PASSWORD']).decode()
    else:
        dsn_components = parse_dsn(dsn)
        database_password = boto3.client('rds').generate_db_auth_token(dsn_components['host'], 5432, dsn_components['user'])

    db_connection = create_db_connection(dsn, database_password)
    logger.info('Created connection to DB')

    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        filename = record['s3']['object']['key']

        iterable = fetch_import_file(bucket, filename)

        for line in iterable:
            try:
                message_envelope = json.loads(line)
                event = event_from_json_object(message_envelope['document'])

                if write_audit_event_to_database(event, db_connection):
                    if event.event_type == 'session_event' and event.details.get('session_event_type') == 'idp_authn_succeeded':
                        write_billing_event_to_database(event, db_connection)
                    if event.event_type == 'session_event' and event.details.get('session_event_type') == 'fraud_detected':
                        write_fraud_event_to_database(event, db_connection)

            except Exception as exception:
                logger.exception('Failed to store message{}'.format(exception))

        delete_import_file(bucket, filename)
