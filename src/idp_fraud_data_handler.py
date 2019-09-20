import csv
import logging
import os
import re

import dateparser

from src.common import get_database_password
from src.database import create_db_connection, write_import_session, write_idp_fraud_event_to_database, \
    update_session_as_validated, write_upload_error, RunInTransaction
from src.idp_fraud_event import IdpFraudEvent
from src.s3 import fetch_object_tags, move_file, download_import_file
from src.upload_session import UploadSession

SUCCESS_FOLDER = 'success'
ERROR_FOLDER = 'error'
DEFAULT_TIMEZONE = 'Europe/London'
DEFAULT_HAS_HEADER = True
DEFAULT_DIALECT = 'excel'
logger = logging.getLogger('idp_fraud_data_handler')
logger.setLevel(logging.INFO)


def create_import_session(filename, idp_entity_id, userid, db_connection):
    upload_session = UploadSession(
        source_file_name=filename,
        idp_entity_id=idp_entity_id,
        userid=userid
    )
    return write_import_session(upload_session, db_connection, logger)


def process_file(bucket, filename, upload_session, db_connection,
                 has_header=DEFAULT_HAS_HEADER, dialect=DEFAULT_DIALECT, timezone=DEFAULT_TIMEZONE):
    logger.info('Processing data for IDP {}'.format(upload_session.idp_entity_id))

    temp_file = download_import_file(bucket, filename)
    with open(temp_file, newline='') as csvfile:
        reader = csv.reader(csvfile, dialect=dialect)
        errors_occurred = False
        skip_row = has_header
        row_number = 0
        try:
            with RunInTransaction(db_connection) as cursor:
                for row in reader:
                    row_number = row_number + 1
                    if skip_row:
                        skip_row = False
                        continue

                    idp_fraud_event = parse_line(row, upload_session.idp_entity_id, timezone)
                    event_id = write_idp_fraud_event_to_database(upload_session, idp_fraud_event, cursor, logger)
                    if event_id:
                        logger.info(
                            'Successfully wrote IDP fraud event ID {} to database and '
                            'found matching fraud event {}'.format(idp_fraud_event.idp_event_id, event_id)
                        )
                    else:
                        logger.warning(
                            'Successfully wrote IDP fraud event ID {} to database BUT '
                            'no matching fraud event found'.format(idp_fraud_event.idp_event_id)
                        )

        except Exception as exception:
            message = 'Failed to store IDP fraud event: {} (line {})'.format(exception, row_number)
            logger.exception(message)
            write_upload_error(upload_session, row_number, '**Row Exception**', message, db_connection)
            errors_occurred = True

    os.remove(temp_file)
    return not errors_occurred


def parse_line(row, idp_entity_id, timezone=DEFAULT_TIMEZONE):
    return IdpFraudEvent(
        idp_entity_id=idp_entity_id,
        timestamp=dateparser.parse(row[0], settings={'TIMEZONE': timezone}),
        idp_event_id=row[1],
        fid_code=row[2],
        contra_indicators=re.split(',|\n|\r\n', row[3]) if row[3].strip() else [],
        contra_score=row[4] if row[4].strip() else 0,
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

        tags = fetch_object_tags(bucket, filename)
        idp_entity_id = tags['idp']
        username = tags['username']

        timezone = DEFAULT_TIMEZONE
        dialect = DEFAULT_DIALECT
        has_header = DEFAULT_HAS_HEADER

        if 'timezone' in tags:
            timezone = tags['timezone']
        if 'dialect' in tags:
            dialect = tags['dialect']
        if 'has_header' in tags:
            has_header = tags['has_header'].lower() in ['true', '1', 'y', 'yes']

        upload_session = create_import_session(filename, idp_entity_id, username, db_connection)
        if process_file(bucket, filename, upload_session, db_connection, has_header, dialect, timezone):
            logger.info("Processing successful")
            update_session_as_validated(upload_session, db_connection)
            move_to_success(bucket, filename)
        else:
            logger.warning("Processing Failed")
            move_to_error(bucket, filename)
