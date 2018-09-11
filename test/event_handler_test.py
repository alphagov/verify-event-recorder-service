import os
import boto3
import base64
import json
import uuid
import psycopg2
from moto import mock_sqs, mock_s3, mock_kms
from unittest import TestCase
from datetime import datetime
from testfixtures import LogCapture
from retrying import retry

from src import event_handler
from src.database import RunInTransaction
from test.test_encrypter import encrypt_string

EVENT_TYPE = 'session_event'
TIMESTAMP = 1518264452000 # '2018-02-10 12:07:32'
SESSION_EVENT_TYPE = 'success'
ORIGINATING_SERVICE = 'test service'
SESSION_ID = 'test session id'
ENCRYPTION_KEY = b'sixteen byte key'
DB_PASSWORD = 'secretPassword'

@mock_sqs
@mock_s3
@mock_kms
class EventHandlerTest(TestCase):
    __sqs_client = None
    __s3_client = None
    __kms_client = None
    __queue_url = None
    __key_id = None
    db_connection = None
    db_connection_string = "host='event-store' dbname='postgres' user='postgres'"

    @classmethod
    def setUpClass(cls):
        cls.connect()

    @classmethod
    @retry(stop_max_attempt_number=5, wait_fixed=500)
    def connect(cls):
        cls.db_connection = psycopg2.connect(cls.db_connection_string)

    def setUp(self):
        setup_stub_aws_config()
        self.__setup_kms()
        self.__setup_db_connection_string()
        self.__setup_sqs()

    def tearDown(self):
        self.__clean_db()

    def test_reads_messages_from_queue_with_key_from_s3(self):
        self.__setup_s3()
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

    def test_reads_messages_from_queue_with_key_from_env(self):
        os.environ['ENCRYPTION_KEY'] = self.__encrypt(ENCRYPTION_KEY)
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

    def test_writes_messages_to_db_with_password_from_env(self):
        self.__setup_s3()
        self.__setup_db_connection_string(True)
        self.__encrypt_and_send_to_sqs(
            [
                create_event_string('sample-id-1'),
                create_event_string('sample-id-2'),
            ]
        )

        event_handler.store_queued_events(None, None)

        self.__assert_database_has_records(['sample-id-1', 'sample-id-2'])

    def test_does_not_delete_invalid_messages(self):
        self.__setup_s3()
        with LogCapture('event-recorder', propagate=False) as log_capture:
            self.__encrypt_and_send_to_sqs(
                [
                    'invalid event',
                    create_event_string('sample-id-2'),
                ]
            )

            event_handler.store_queued_events(None, None)

            self.__assert_database_has_records(['sample-id-2'])
            log_capture.check(
                (
                    'event-recorder',
                    'ERROR',
                    'Failed to store message'
                )
            )
            self.assertEqual(self.__number_of_visible_messages(), '0')
            self.assertEqual(self.__number_of_hidden_messages(), '1')

    def test_records_error_but_does_delete_messages_for_duplicate_events(self):
        self.__setup_s3()
        with LogCapture('event-recorder', propagate=False) as log_capture:
            self.__encrypt_and_send_to_sqs(
                [
                    create_event_string('sample-id-1'),
                    create_event_string('sample-id-1'),
                ]
            )

            event_handler.store_queued_events(None, None)

            self.__assert_database_has_records(['sample-id-1'])
            log_capture.check(
                (
                    'event-recorder',
                    'WARNING',
                    'Failed to store message. The Event ID sample-id-1 already exists in the database'
                )
            )
            self.assertEqual(self.__number_of_visible_messages(), '0')
            self.assertEqual(self.__number_of_hidden_messages(), '0')

    def __encrypt_and_send_to_sqs(self, messages):
        for message in messages:
            encrypted_message = encrypt_string(message, ENCRYPTION_KEY)
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
                DELETE FROM audit.audit_events;
            """)

    def __assert_database_has_records(self, expected_event_ids):
        for event_id in expected_event_ids:
            with RunInTransaction(self.db_connection) as cursor:
                cursor.execute("""
                    SELECT
                        event_id,
                        event_type,
                        time_stamp,
                        originating_service,
                        session_id,
                        details
                    FROM
                        audit.audit_events
                    WHERE
                        event_id = %s;
                """, [event_id])
                matching_records = cursor.fetchone()

            self.assertIsNotNone(matching_records)
            self.assertEqual(matching_records[0], event_id)
            self.assertEqual(matching_records[1], EVENT_TYPE)
            self.assertEqual(matching_records[2], datetime.fromtimestamp(TIMESTAMP / 1e3))
            self.assertEqual(matching_records[3], ORIGINATING_SERVICE)
            self.assertEqual(matching_records[4], SESSION_ID)
            self.assertEqual(matching_records[5], {'sessionEventType': SESSION_EVENT_TYPE})

    def __setup_db_connection_string(self, password_in_env=False):
        if password_in_env:
          os.environ['DB_CONNECTION_STRING'] = self.db_connection_string
          os.environ['ENCRYPTED_DATABASE_PASSWORD'] = self.__encrypt(DB_PASSWORD)
        else:
          os.environ['DB_CONNECTION_STRING'] = "{} password='{}'".format(self.db_connection_string, DB_PASSWORD)

    def __setup_sqs(self):
        self.__sqs_client = boto3.client('sqs')
        queue = self.__sqs_client.create_queue(
            QueueName=str(uuid.uuid4()),
        )
        self.__queue_url = queue['QueueUrl']
        os.environ['QUEUE_URL'] = self.__queue_url

    def __setup_kms(self):
        self.__kms_client = boto3.client('kms')
        response = self.__kms_client.create_key(
            KeyUsage='ENCRYPT_DECRYPT',
            Origin='AWS_KMS',
        )
        self.__key_id = response['KeyMetadata']['KeyId']

    def __setup_s3(self):
        self.__s3_client = boto3.client('s3')
        self.__s3_client.create_bucket(
            Bucket='key-bucket',
        )
        self.__write_encryption_key_to_s3()

    def __encrypt(self, content):
        response = self.__kms_client.encrypt(
            KeyId=self.__key_id,
            Plaintext=content,
        )
        # The boto3 client provides CiphertextBlob as binary, the CLI uses base64
        return base64.b64encode(response['CiphertextBlob'])

    def __write_encryption_key_to_s3(self):
        bucket_name = 'key-bucket'
        filename = 'encrypted-event-key.txt'
        encrypted_encryption_key = self.__encrypt(ENCRYPTION_KEY)
        self.__s3_client.put_object(
            Bucket=bucket_name,
            Key=filename,
            Body=encrypted_encryption_key
        )
        os.environ['DECRYPTION_KEY_BUCKET_NAME'] = bucket_name
        os.environ['DECRYPTION_KEY_FILE_NAME'] = filename


def setup_stub_aws_config():
    os.environ = {
        'AWS_DEFAULT_REGION': 'eu-west-2',
    }


def create_event_string(event_id):
    return json.dumps({
        'eventId': event_id,
        'eventType': EVENT_TYPE,
        'timestamp': TIMESTAMP,
        'originatingService': ORIGINATING_SERVICE,
        'sessionId': SESSION_ID,
        'details': {
            'sessionEventType': SESSION_EVENT_TYPE
        }
    })
