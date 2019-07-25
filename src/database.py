import json
import psycopg2
import os
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
            getLogger('event-recorder').warning('Failed to store an audit event. The Event ID {0} already exists in the database'.format(event.event_id))
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
                    required_level_of_assurance,
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
                event.details['required_level_of_assurance'],
                event.details['provided_level_of_assurance'],
                event.event_id,
                event.details['transaction_entity_id']
            ])
    except KeyError as keyError:
        getLogger('event-recorder').warning('Failed to store a billing event [Event ID {0}] due to key error'.format(event.event_id))
        raise keyError
    except IntegrityError as integrityError:
        if integrityError.pgcode == UNIQUE_VIOLATION:
            # The event has already been recorded - don't throw an exception (no need to retry this message), just
            # log a notification and move on.
            getLogger('event-recorder').warning('Failed to store a billing event. The Event ID {0} already exists in the database'.format(event.event_id))
        else:
            getLogger('event-recorder').warning('Failed to store a billing event [Event ID {0}] due to integrity error'.format(event.event_id))
            raise integrityError


def write_fraud_event_to_database(event, db_connection):
    try:
        with RunInTransaction(db_connection) as cursor:
            cursor.execute("""
                INSERT INTO billing.fraud_events
                (time_stamp, session_id, hashed_persistent_id, request_id, entity_id, fraud_event_id, fraud_indicator)
                VALUES
                (%s, %s, %s, %s, %s, %s, %s);
            """, [
                datetime.fromtimestamp(int(event.timestamp) / 1e3),
                event.session_id,
                event.details['pid'],
                event.details['request_id'],
                event.details['idp_entity_id'],
                event.details['idp_fraud_event_id'],
                event.details['gpg45_status']
            ])
    except KeyError as keyError:
        getLogger('event-recorder').warning('Failed to store a fraud event [Event ID {0}] due to key error'.format(event.event_id))
        raise keyError
    except IntegrityError as integrityError:
        getLogger('event-recorder').warning('Failed to store a fraud event [Event ID {0}] due to integrity error'.format(event.event_id))
        raise integrityError
