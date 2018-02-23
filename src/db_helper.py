import psycopg2
import os


def create_db_connection():
    return psycopg2.connect(os.environ['DB_CONNECTION_STRING'])


class RunInTransaction:

    def __init__(self, connection):
        self.__connection = connection

    def __enter__(self):
        return self.__connection.cursor()

    def __exit__(self, type, value, traceback):
        self.__connection.commit()
