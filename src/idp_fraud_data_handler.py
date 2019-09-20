import logging
import os
import boto3
import csv
import codecs
import dateutil.parser

from src.database import create_db_connection, write_import_session, write_idp_fraud_event_to_database
from src.s3 import fetch_import_file, fetch_object_tags, delete_import_file
from src.kms import decrypt
from src.idp_fraud_event import IdpFraudEvent
from psycopg2.extensions import parse_dsn

logger = logging.getLogger('idp_fraud_data_handler')
logger.setLevel(logging.INFO)


def create_import_session(bucket, filename, db_connection):
    tags = fetch_object_tags(bucket, filename)
    idp_entity_id = tags['idp']
    username = tags['username']
    return write_import_session(filename, idp_entity_id, username, db_connection)


def process_file(bucket, filename, session, idp_entity_id, db_connection, skip_header=True):
    iterable = fetch_import_file(bucket, filename)
    reader = csv.reader(codecs.iterdecode(iterable, 'utf-8'), dialect="excel")
    errors_occurred = False
    skip_row = skip_header
    for row in reader:
        if skip_row:
            skip_row = False
            continue

        try:
            idp_fraud_event = parse_line(row, idp_entity_id)
            write_idp_fraud_event_to_database(session, idp_fraud_event, db_connection)

        except Exception as exception:
            message = 'Failed to store message {}'.format(exception)
            logger.exception(message)
            write_to_error_log(session, message)
            errors_occurred = True

    return not errors_occurred


def parse_line(row, idp_entity_id):
    return IdpFraudEvent(
        idp_entity_id=idp_entity_id,
        timestamp=dateutil.parser.parse(row[0]),
        idp_event_id=row[1],
        fid_code=row[2],
        contra_indicators=row[3].split(","),
        contra_score=row[4],
        request_id=row[5],
        client_ip_address=row[6],
        pid=row[7]
    )


def write_to_error_log(session, message):
    pass


def move_to_error(bucket, filename):
    pass


def move_to_success(bucket, filename):
    delete_import_file(bucket, filename)


def idp_fraud_data_events(event, __):
    dsn = os.environ['DB_CONNECTION_STRING']

    database_password = None
    if 'ENCRYPTED_DATABASE_PASSWORD' in os.environ:
        # boto returns decrypted as b'bytes' so decode to convert to password string
        database_password = decrypt(os.environ['ENCRYPTED_DATABASE_PASSWORD']).decode()
    else:
        dsn_components = parse_dsn(dsn)
        database_password = boto3.client('rds').generate_db_auth_token(
            dsn_components['host'], 5432, dsn_components['user'])

    db_connection = create_db_connection(dsn, database_password)
    logger.info('Created connection to DB')

    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        filename = record['s3']['object']['key']

        session, idp_entity_id = create_import_session(bucket, filename, db_connection)

        if process_file(bucket, filename, session, idp_entity_id, db_connection):
            move_to_success(bucket, filename)
        else:
            move_to_error(bucket, filename)
