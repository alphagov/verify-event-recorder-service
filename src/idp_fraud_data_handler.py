import logging
import os
import boto3
import csv
import codecs
import dateutil.parser

from src.database import create_db_connection, write_import_session, write_idp_fraud_event_to_database, \
    update_session_as_validated, write_upload_error
from src.s3 import fetch_import_file, fetch_object_tags, move_file
from src.kms import decrypt
from src.idp_fraud_event import IdpFraudEvent
from src.common import get_database_password

SUCCESS_FOLDER='success'
ERROR_FOLDER='error'
logger = logging.getLogger('idp_fraud_data_handler')
logger.setLevel(logging.INFO)


def create_import_session(bucket, filename, db_connection):
    tags = fetch_object_tags(bucket, filename)
    idp_entity_id = tags['idp']
    username = tags['username']
    return write_import_session(filename, idp_entity_id, username, db_connection, logger)


def process_file(bucket, filename, session, idp_entity_id, db_connection, skip_header=True):
    logger.info('Processing data for IDP {}'.format(idp_entity_id))
    iterable = fetch_import_file(bucket, filename)
    reader = csv.reader(codecs.iterdecode(iterable, 'utf-8'), dialect="excel")
    errors_occurred = False
    skip_row = skip_header
    row_number = 0
    for row in reader:
        row_number = row_number + 1
        if skip_row:
            skip_row = False
            continue

        try:
            idp_fraud_event = parse_line(row, idp_entity_id)
            event_id = write_idp_fraud_event_to_database(session, idp_fraud_event, db_connection, logger)
            if event_id:
                logger.info('Successfully wrote IDP fraud event ID {} to database and found matching fraud event {}'.format(idp_fraud_event.idp_event_id, event_id))
            else:
                logger.warning('Successfully wrote IDP fraud event ID {} to database BUT no matching fraud event found'.format(idp_fraud_event.idp_event_id))

        except Exception as exception:
            message = 'Failed to store IDP fraud event: {} (line {})'.format(exception, row_number)
            logger.exception(message)
            write_upload_error(session, row_number, '**Row Exception**', message, db_connection)
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


def move_to_error(bucket, filename):
    move_file(bucket, filename, ERROR_FOLDER)


def move_to_success(bucket, filename):
    move_file(bucket, filename, SUCCESS_FOLDER)


def idp_fraud_data_events(event, __):
    dsn = os.environ['DB_CONNECTION_STRING']

    db_connection = create_db_connection(dsn, get_database_password(dsn))
    logger.info('Created connection to DB')

    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        filename = record['s3']['object']['key']

        session, idp_entity_id = create_import_session(bucket, filename, db_connection)

        if process_file(bucket, filename, session, idp_entity_id, db_connection):
            update_session_as_validated(session, db_connection)
            move_to_success(bucket, filename)
        else:
            move_to_error(bucket, filename)
