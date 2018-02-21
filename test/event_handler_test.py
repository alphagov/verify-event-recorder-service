import os
import boto3
import io
import json
import uuid
import psycopg2
from moto import mock_sqs
from unittest import TestCase
from unittest.mock import patch
from datetime import datetime

from src import event_handler
from src.db_helper import RunInTransaction

EVENT_TYPE = 'session_event'
TIMESTAMP = '2018-02-10 12:07:32'
SESSION_EVENT_TYPE = 'success'

@mock_sqs
class EventHandlerTest(TestCase):
    __sqs_client = None
    __queue_url = None
    db_connection = None
    db_connection_string = "host='localhost' dbname='postgres' user='postgres' password='secretPassword'"

    @classmethod
    def setUpClass(cls):
        cls.db_connection = psycopg2.connect(cls.db_connection_string)
        with RunInTransaction(cls.db_connection) as cursor:
            cursor.execute("""
                CREATE TABLE events (
                    event_id VARCHAR(40) NOT NULL PRIMARY KEY,
                    event_type VARCHAR(20) NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    details JSON NOT NULL
                );
            """)

    @classmethod
    def tearDownClass(cls):
        with RunInTransaction(cls.db_connection) as cursor:
            cursor.execute("""
                DROP TABLE events;
            """)

    def setUp(self):
        setup_stub_aws_config()
        self.__sqs_client = boto3.client('sqs')
        self.__queue_url = create_queue(self.__sqs_client)
        add_queue_url_to_environment_variables(self.__queue_url)
        add_connection_string_to_environment_variables(self.db_connection_string)

    def tearDown(self):
        self.__clean_db()

    def test_reads_messages_from_queue(self):
        self.__send_messages_to_queue(
            [
                create_event_string('sample-id-1'),
                create_event_string('sample-id-2'),
            ]
        )

        event_handler.store_queued_events(None, None)

        self.__assert_database_has_records(['sample-id-1', 'sample-id-2'])
        self.assertEqual(self.__number_of_visible_messages(), '0')
        self.assertEqual(self.__number_of_hidden_messages(), '0')

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_does_not_delete_invalid_messages(self, mock_stdout):
        self.__send_messages_to_queue(
            [
                'invalid event',
                create_event_string('sample-id-2'),
            ]
        )

        event_handler.store_queued_events(None, None)

        self.__assert_database_has_records(['sample-id-2'])
        self.assertRegex(mock_stdout.getvalue(), 'Failed to store message - Exception:')
        self.assertEqual(self.__number_of_visible_messages(), '0')
        self.assertEqual(self.__number_of_hidden_messages(), '1')

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_records_error_but_does_delete_messages_for_duplicate_events(self, mock_stdout):
        self.__send_messages_to_queue(
            [
                create_event_string('sample-id-1'),
                create_event_string('sample-id-1'),
            ]
        )

        event_handler.store_queued_events(None, None)

        self.__assert_database_has_records(['sample-id-1'])
        self.assertEqual(
            mock_stdout.getvalue(),
            'Failed to store message. The Event ID sample-id-1 already exists in the database\n')
        self.assertEqual(self.__number_of_visible_messages(), '0')
        self.assertEqual(self.__number_of_hidden_messages(), '0')

    def __send_messages_to_queue(self, messages):
        for message in messages:
            self.__sqs_client.send_message(
                QueueUrl=self.__queue_url,
                MessageBody=message,
                DelaySeconds=0
            )

    def __number_of_visible_messages(self):
        return self.__get_attribute('ApproximateNumberOfMessages')

    def __number_of_hidden_messages(self):
        return self.__get_attribute('ApproximateNumberOfMessagesNotVisible')

    def __get_attribute(self, attribute):
        response = self.__sqs_client.get_queue_attributes(
            QueueUrl=self.__queue_url,
            AttributeNames=[attribute]
        )
        return response['Attributes'][attribute]

    def __clean_db(self):
        with RunInTransaction(self.db_connection) as cursor:
            cursor.execute("""
                DELETE FROM events;
            """)

    def __assert_database_has_records(self, expected_event_ids):
        for event_id in expected_event_ids:
            with RunInTransaction(self.db_connection) as cursor:
                cursor.execute("""
                    SELECT * FROM events WHERE event_id = '%s';
                """ % event_id)
                matching_records = cursor.fetchone()

            self.assertEqual(matching_records[0], event_id)
            self.assertEqual(matching_records[1], EVENT_TYPE)
            self.assertEqual(matching_records[2], datetime.strptime(TIMESTAMP, '%Y-%m-%d %H:%M:%S'))
            self.assertEqual(matching_records[3], {'sessionEventType': SESSION_EVENT_TYPE})


def setup_stub_aws_config():
    os.environ = {
        'AWS_DEFAULT_REGION': 'eu-west-2',
    }


def create_queue(sqs_client):
    queue = sqs_client.create_queue(
        QueueName=str(uuid.uuid4()),
    )
    return queue['QueueUrl']


def add_queue_url_to_environment_variables(queue_url):
    os.environ['QUEUE_URL'] = queue_url


def add_connection_string_to_environment_variables(connection_string):
    os.environ['DB_CONNECTION_STRING'] = connection_string


def create_event_string(event_id):
    return json.dumps({
        'eventId': event_id,
        'eventType': EVENT_TYPE,
        'timestamp': TIMESTAMP,
        'details': {
            'sessionEventType': SESSION_EVENT_TYPE
        }
    })
