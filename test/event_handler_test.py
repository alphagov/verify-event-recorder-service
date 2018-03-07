import os
import boto3
import io
import json
import uuid
import psycopg2
from moto import mock_sqs, mock_s3
from unittest import TestCase
from unittest.mock import patch
from datetime import datetime
from Crypto.Cipher import AES

from src import event_handler
from src.database import RunInTransaction
from test.test_encrypter import encrypt_string

EVENT_TYPE = 'session_event'
TIMESTAMP = '2018-02-10 12:07:32'
SESSION_EVENT_TYPE = 'success'
ENCRYPTION_KEY = b'sixteen byte key'


@mock_sqs
@mock_s3
class EventHandlerTest(TestCase):
    __sqs_client = None
    __s3_client = None
    __queue_url = None
    __key_id = None
    db_connection = None
    db_connection_string = "host='localhost' dbname='postgres' user='postgres' password='secretPassword'"

    @classmethod
    def setUpClass(cls):
        cls.db_connection = psycopg2.connect(cls.db_connection_string)

    def setUp(self):
        setup_stub_aws_config()
        self.__setup_db_connection()
        self.__setup_sqs()
        self.__setup_s3()

    def tearDown(self):
        self.__clean_db()

    def test_reads_messages_from_queue(self):
        self.__encrypt_and_send_to_sqs(
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
        self.__encrypt_and_send_to_sqs(
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
        self.__encrypt_and_send_to_sqs(
            [
                create_event_string('sample-id-1'),
                create_event_string('sample-id-1'),
            ]
        )

        event_handler.store_queued_events(None, None)

        self.__assert_database_has_records(['sample-id-1'])
        self.assertRegex(
            mock_stdout.getvalue(),
            'Failed to store message. The Event ID sample-id-1 already exists in the database\n')
        self.assertEqual(self.__number_of_visible_messages(), '0')
        self.assertEqual(self.__number_of_hidden_messages(), '0')

    def __encrypt_and_send_to_sqs(self, messages):
        for message in messages:
            encrypted_message = encrypt_string(pad(message), ENCRYPTION_KEY)
            self.__sqs_client.send_message(
                QueueUrl=self.__queue_url,
                MessageBody=encrypted_message,
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
                    SELECT * FROM events WHERE event_id = %s;
                """, [event_id])
                matching_records = cursor.fetchone()

            self.assertIsNotNone(matching_records)
            self.assertEqual(matching_records[0], event_id)
            self.assertEqual(matching_records[1], EVENT_TYPE)
            self.assertEqual(matching_records[2], datetime.strptime(TIMESTAMP, '%Y-%m-%d %H:%M:%S'))
            self.assertEqual(matching_records[3], {'sessionEventType': SESSION_EVENT_TYPE})

    def __setup_db_connection(self):
        os.environ['DB_CONNECTION_STRING'] = self.db_connection_string

    def __setup_sqs(self):
        self.__sqs_client = boto3.client('sqs')
        queue = self.__sqs_client.create_queue(
            QueueName=str(uuid.uuid4()),
        )
        self.__queue_url = queue['QueueUrl']
        os.environ['QUEUE_URL'] = self.__queue_url

    def __setup_s3(self):
        self.__s3_client = boto3.client('s3')
        self.__s3_client.create_bucket(
            Bucket='key-bucket',
        )
        self.__write_encryption_key_to_s3()

    def __write_encryption_key_to_s3(self):
        bucket_name = 'key-bucket'
        filename = 'encrypted-event-key.txt'
        self.__s3_client.put_object(
            Bucket=bucket_name,
            Key=filename,
            Body=ENCRYPTION_KEY
        )
        os.environ['DECRYPTION_KEY_BUCKET_NAME'] = bucket_name
        os.environ['DECRYPTION_KEY_FILE_NAME'] = filename


def pad(text):
    number_of_characters = AES.block_size - (len(text) % AES.block_size)
    return text + number_of_characters * chr(number_of_characters)


def setup_stub_aws_config():
    os.environ = {
        'AWS_DEFAULT_REGION': 'eu-west-2',
    }


def create_event_string(event_id):
    return json.dumps({
        'eventId': event_id,
        'eventType': EVENT_TYPE,
        'timestamp': TIMESTAMP,
        'details': {
            'sessionEventType': SESSION_EVENT_TYPE
        }
    })
