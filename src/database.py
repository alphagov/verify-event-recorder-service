import json
import psycopg2
from datetime import datetime

from psycopg2._psycopg import IntegrityError
from psycopg2.errorcodes import UNIQUE_VIOLATION
from logging import getLogger


def create_db_connection(dsn, database_password):
    if database_password:
        return psycopg2.connect(dsn, password=database_password)
    return psycopg2.connect(dsn)


class RunInTransaction:

    def __init__(self, connection):
        self.__connection = connection

    def __enter__(self):
        return self.__connection.cursor()

    def __exit__(self, type, value, traceback):
        if type is None:
            self.__connection.commit()
        else:
            self.__connection.rollback()


def write_audit_event_to_database(event, db_connection):
    try:
        with RunInTransaction(db_connection) as cursor:
            cursor.execute("""
                INSERT INTO audit.audit_events
                (event_id, event_type, time_stamp, originating_service, session_id, details)
                VALUES
                (%s, %s, %s, %s, %s, %s);
            """, [
                event.event_id,
                event.event_type,
                datetime.fromtimestamp(int(event.timestamp) / 1e3),
                event.originating_service,
                event.session_id,
                json.dumps(event.details)
            ])
    except IntegrityError as integrityError:
        if integrityError.pgcode == UNIQUE_VIOLATION:
            # The event has already been recorded - don't throw an exception (no need to retry this message), just
            # log a notification and move on.
            getLogger('event-recorder').warning(
                'Failed to store an audit event. The Event ID {0} already exists in the database'.format(
                    event.event_id))
            return False
        else:
            raise integrityError

    return True


def write_billing_event_to_database(event, db_connection):
    try:
        with RunInTransaction(db_connection) as cursor:
            cursor.execute("""
                INSERT INTO billing.billing_events
                (
                    time_stamp,
                    session_id,
                    hashed_persistent_id,
                    request_id,
                    idp_entity_id,
                    minimum_level_of_assurance,
                    preferred_level_of_assurance,
                    provided_level_of_assurance,
                    event_id,
                    transaction_entity_id
                )
                VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, [
                datetime.fromtimestamp(int(event.timestamp) / 1e3),
                event.session_id,
                event.details['pid'],
                event.details['request_id'],
                event.details['idp_entity_id'],
                event.details['minimum_level_of_assurance'],
                event.details['preferred_level_of_assurance'],
                event.details['provided_level_of_assurance'],
                event.event_id,
                event.details['transaction_entity_id']
            ])
    except KeyError as keyError:
        getLogger('event-recorder').warning(
            'Failed to store a billing event [Event ID {0}] due to key error'.format(event.event_id))
        raise keyError
    except IntegrityError as integrityError:
        if integrityError.pgcode == UNIQUE_VIOLATION:
            # The event has already been recorded - don't throw an exception (no need to retry this message), just
            # log a notification and move on.
            getLogger('event-recorder').warning(
                'Failed to store a billing event. The Event ID {0} already exists in the database'.format(
                    event.event_id))
        else:
            getLogger('event-recorder').warning(
                'Failed to store a billing event [Event ID {0}] due to integrity error'.format(event.event_id))
            raise integrityError


def write_fraud_event_to_database(event, db_connection):
    try:
        with RunInTransaction(db_connection) as cursor:
            cursor.execute("""
                INSERT INTO billing.fraud_events
                (
                    event_id,
                    time_stamp,
                    session_id,
                    hashed_persistent_id,
                    request_id,
                    entity_id,
                    fraud_event_id,
                    fraud_indicator,
                    transaction_entity_id
                )
                VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, [
                event.event_id,
                datetime.fromtimestamp(int(event.timestamp) / 1e3),
                event.session_id,
                event.details['pid'],
                event.details['request_id'],
                event.details['idp_entity_id'],
                event.details['idp_fraud_event_id'],
                event.details['gpg45_status'],
                event.details['transaction_entity_id']
            ])
    except KeyError as keyError:
        getLogger('event-recorder').warning(
            'Failed to store a fraud event [Event ID {0}] due to key error'.format(event.event_id))
        raise keyError
    except IntegrityError as integrityError:
        if integrityError.pgcode == UNIQUE_VIOLATION:
            # The event has already been recorded - don't throw an exception (no need to retry this message), just
            # log a notification and move on.
            getLogger('event-recorder').warning(
                'Failed to store a fraud event. The Event ID {0} already exists in the database'.format(event.event_id))
        else:
            getLogger('event-recorder').warning(
                'Failed to store a fraud event [Event ID {0}] due to integrity error'.format(event.event_id))
            raise integrityError


def write_import_session(upload_session, db_connection, logger):
    try:
        with RunInTransaction(db_connection) as cursor:
            cursor.execute("""
                INSERT INTO idp_data.upload_sessions
                (
                    time_stamp,
                    source_file_name,
                    idp_entity_id,
                    userid,
                    passed_validation
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    FALSE
                )
                RETURNING id
            """, [upload_session.time_stamp,
                  upload_session.source_file_name,
                  upload_session.idp_entity_id,
                  upload_session.userid])

            result = cursor.fetchone()
            upload_session.id = result[0]
            return upload_session

    except KeyError as keyError:
        logger.exception(
            'Failed to store upload session for file {}, idp = {} due to key error'.format(
                upload_session.source_file_name, upload_session.idp_entity_id)
        )
        raise keyError
    except IntegrityError as integrityError:
        logger.exception(
            'Failed to store upload session for file {}, idp = {} due to integrity error'.format(
                upload_session.source_file_name, upload_session.idp_entity_id)
        )
        raise integrityError


def write_idp_fraud_event_to_database(upload_session, idp_fraud_event, cursor, logger):
    try:
        cursor.execute("""
             INSERT INTO idp_data.idp_fraud_events
             (
                idp_entity_id,
                idp_event_id,
                time_stamp,
                fid_code,
                request_id,
                pid,
                client_ip_address,
                contra_score,
                upload_session_id
             )
             VALUES
             (
                %(idp_entity_id)s,
                %(idp_event_id)s,
                %(timestamp)s,
                %(fid_code)s,
                %(request_id)s,
                %(pid)s,
                %(client_ip_address)s,
                %(contra_score)s,
                %(session_id)s
             )
             RETURNING id
             ;
         """, {
            "idp_entity_id": idp_fraud_event.idp_entity_id,
            "idp_event_id": idp_fraud_event.idp_event_id,
            "timestamp": idp_fraud_event.timestamp,
            "fid_code": idp_fraud_event.fid_code,
            "request_id": idp_fraud_event.request_id,
            "pid": idp_fraud_event.pid,
            "client_ip_address": idp_fraud_event.client_ip_address,
            "contra_score": idp_fraud_event.contra_score,
            "session_id": upload_session.id
        })

        result = cursor.fetchone()
        id = result[0]

        for contra_indicator in idp_fraud_event.contra_indicators:
            cursor.execute("""
                INSERT INTO idp_data.idp_fraud_event_contraindicators
                (
                    idp_fraud_events_id,
                    contraindicator_code
                )
                VALUES
                (
                    %s,
                    %s
                )
                ON CONFLICT (idp_fraud_events_id, contraindicator_code)
                DO UPDATE SET count = idp_fraud_event_contraindicators.count + 1
            """, [id, contra_indicator])
        return result[0]

    except KeyError as keyError:
        logger.exception(
            'Failed to store an IDP fraud event [Event ID {}] due to key error'.format(idp_fraud_event.idp_event_id))
        raise keyError
    except IntegrityError as integrityError:
        logger.exception(
            'Failed to store an IDP fraud event [Event ID {}] due to integrity error'.format(
                idp_fraud_event.idp_event_id
            )
        )
        raise integrityError


def update_session_as_validated(upload_session, db_connection):
    with RunInTransaction(db_connection) as cursor:
        cursor.execute("""
            UPDATE idp_data.upload_sessions
               SET passed_validation = TRUE
             WHERE id = %s
        """, [upload_session.id])


def write_upload_error(upload_session, row, field, message, db_connection):
    with RunInTransaction(db_connection) as cursor:
        cursor.execute("""
            INSERT INTO idp_data.upload_session_validation_failures
            (
                upload_session_id,
                row,
                field,
                message
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s
            )
        """, [upload_session.id, row, field, message])
