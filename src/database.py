import json
import psycopg2
import os
from datetime import datetime

from psycopg2._psycopg import IntegrityError
from psycopg2.errorcodes import UNIQUE_VIOLATION
from logging import getLogger


def create_db_connection():
    return psycopg2.connect(os.environ['DB_CONNECTION_STRING'])


class RunInTransaction:

    def __init__(self, connection):
        self.__connection = connection

    def __enter__(self):
        return self.__connection.cursor()

    def __exit__(self, type, value, traceback):
        self.__connection.commit()


def write_to_database(event, db_connection):
    try:
        with RunInTransaction(db_connection) as cursor:
            cursor.execute("""
                INSERT INTO events
                (event_id, event_type, timestamp, details)
                VALUES
                (%s, %s, %s, %s);
            """, [
                event.event_id,
                event.event_type,
                datetime.fromtimestamp(int(event.timestamp) / 1e3),
                json.dumps(event.details)
            ])
    except IntegrityError as integrityError:
        if integrityError.pgcode == UNIQUE_VIOLATION:
            # The event has already been recorded - don't throw an exception (no need to retry this message), just
            # log a notification and move on.
            getLogger('event-recorder').warning('Failed to store message. The Event ID {0} already exists in the database'.format(event.event_id))
        else:
            raise integrityError
