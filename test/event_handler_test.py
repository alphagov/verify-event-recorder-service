import base64
import os
import uuid
from datetime import datetime
from unittest import TestCase

import boto3
import psycopg2
from moto import mock_sqs, mock_s3, mock_kms
from retrying import retry
from testfixtures import LogCapture, OutputCapture

from src import event_handler
from src.database import RunInTransaction
from test.helpers import setup_stub_aws_config, clean_db, create_event_string, create_fraud_event_string, \
    MINIMUM_LEVEL_OF_ASSURANCE, ENCRYPTION_KEY, create_billing_event_without_minimum_level_of_assurance_string, \
    create_fraud_event_without_idp_fraud_event_id_string, EVENT_TYPE, TIMESTAMP, ORIGINATING_SERVICE, \
    SESSION_EVENT_TYPE, TRANSACTION_ENTITY_ID, FRAUD_SESSION_EVENT_TYPE, DB_PASSWORD, \
    PID, REQUEST_ID, IDP_ENTITY_ID, PROVIDED_LEVEL_OF_ASSURANCE, PREFERRED_LEVEL_OF_ASSURANCE, GPG45_STATUS
from test.test_encrypter import encrypt_string


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
    db_connection_string = "host='event-store' dbname='events' user='postgres'"

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
        clean_db(self.db_connection)

    def test_reads_messages_from_queue_with_key_from_s3(self):
        self.__setup_s3()
        event_id_3 = str(uuid.uuid4())
        event_id_4 = str(uuid.uuid4())
        self.__encrypt_and_send_to_sqs(
            [
                create_event_string('sample-id-1', 'session-id-1'),
                create_event_string('sample-id-2', 'session-id-2'),
                create_fraud_event_string(event_id_3, 'session-id-3', 'fraud-event-id-1'),
                create_fraud_event_string(event_id_4, 'session-id-4', 'fraud-event-id-2'),
            ]
        )

        event_handler.store_queued_events(None, None)

        self.__assert_audit_events_table_has_billing_event_records(
            [('sample-id-1', 'session-id-1'), ('sample-id-2', 'session-id-2')], MINIMUM_LEVEL_OF_ASSURANCE)
        self.__assert_audit_events_table_has_fraud_event_records(
            [(event_id_3, 'session-id-3', 'fraud-event-id-1'), (event_id_4, 'session-id-4', 'fraud-event-id-2')])
        self.__assert_billing_events_table_has_billing_event_records(
            [('session-id-1', 'sample-id-1'), ('session-id-2', 'sample-id-2')])
        self.__assert_fraud_events_table_has_fraud_event_records(
            [(event_id_3, 'session-id-3', 'fraud-event-id-1'), (event_id_4, 'session-id-4', 'fraud-event-id-2')])
        self.assertEqual(self.__number_of_visible_messages(), '0')
        self.assertEqual(self.__number_of_hidden_messages(), '0')

    def test_reads_fraud_events_from_queue(self):
        self.__setup_s3()
        event_id_1 = str(uuid.uuid4())
        event_id_2 = str(uuid.uuid4())
        self.__encrypt_and_send_to_sqs(
            [
                create_fraud_event_string(event_id_1, 'session-id-1', 'fraud-event-id-1'),
                create_fraud_event_string(event_id_2, 'session-id-2', 'fraud-event-id-2'),
            ]
        )

        event_handler.store_queued_events(None, None)

        self.__assert_audit_events_table_has_fraud_event_records(
            [(event_id_1, 'session-id-1', 'fraud-event-id-1'), (event_id_2, 'session-id-2', 'fraud-event-id-2')])
        self.__assert_billing_events_table_has_no_billing_event_records
        self.__assert_fraud_events_table_has_fraud_event_records(
            [(event_id_1, 'session-id-1', 'fraud-event-id-1'), (event_id_2, 'session-id-2', 'fraud-event-id-2')])
        self.assertEqual(self.__number_of_visible_messages(), '0')
        self.assertEqual(self.__number_of_hidden_messages(), '0')

    def test_reads_messages_from_queue_with_key_from_env(self):
        os.environ['ENCRYPTION_KEY'] = self.__encrypt(ENCRYPTION_KEY)
        self.__encrypt_and_send_to_sqs(
            [
                create_event_string('sample-id-1', 'session-id-1'),
                create_event_string('sample-id-2', 'session-id-2'),
            ]
        )

        event_handler.store_queued_events(None, None)

        self.__assert_audit_events_table_has_billing_event_records(
            [('sample-id-1', 'session-id-1'), ('sample-id-2', 'session-id-2')], MINIMUM_LEVEL_OF_ASSURANCE)
        self.__assert_billing_events_table_has_billing_event_records(
            [('session-id-1', 'sample-id-1'), ('session-id-2', 'sample-id-2')])
        self.__assert_fraud_events_table_has_no_fraud_event_records
        self.assertEqual(self.__number_of_visible_messages(), '0')
        self.assertEqual(self.__number_of_hidden_messages(), '0')

    def test_writes_messages_to_db_with_password_from_env(self):
        self.__setup_s3()
        self.__setup_db_connection_string(True)
        self.__encrypt_and_send_to_sqs(
            [
                create_event_string('sample-id-1', 'session-id-1'),
                create_event_string('sample-id-2', 'session-id-2'),
            ]
        )

        event_handler.store_queued_events(None, None)

        self.__assert_audit_events_table_has_billing_event_records(
            [('sample-id-1', 'session-id-1'), ('sample-id-2', 'session-id-2')], MINIMUM_LEVEL_OF_ASSURANCE)
        self.__assert_billing_events_table_has_billing_event_records(
            [('session-id-1', 'sample-id-1'), ('session-id-2', 'sample-id-2')])

    def test_writes_incomplete_billing_event_to_audit_events_table_but_not_to_billing_events_table(self):
        self.__setup_s3()
        with LogCapture('event-recorder', propagate=False) as log_capture:
            message_ids = self.__encrypt_and_send_to_sqs(
                [
                    create_billing_event_without_minimum_level_of_assurance_string('sample-id-1', 'session-id-1'),
                ]
            )

            event_handler.store_queued_events(None, None)

            self.__assert_audit_events_table_has_billing_event_records([('sample-id-1', 'session-id-1')], None)
            self.__assert_billing_events_table_has_no_billing_event_records
            self.__assert_fraud_events_table_has_no_fraud_event_records
            log_capture.check(
                ('event-recorder', 'INFO', 'Got decryption key from S3'),
                ('event-recorder', 'INFO', 'Decrypted key successfully'),
                ('event-recorder', 'INFO', 'Created connection to DB'),
                ('event-recorder', 'INFO', 'Decrypted event with ID: sample-id-1'),
                ('event-recorder', 'INFO', 'Stored audit event: sample-id-1'),
                ('event-recorder', 'WARNING',
                    'Failed to store a billing event [Event ID sample-id-1] due to key error'),
                ('event-recorder', 'ERROR',
                    'Failed to store event {0}, event type "{1}" from SQS message ID {2}'.format(
                        'sample-id-1', EVENT_TYPE, message_ids[0])),
                ('event-recorder', 'INFO', 'Queue is empty - finishing after 1 events')
            )
            self.assertEqual(self.__number_of_visible_messages(), '0')
            self.assertEqual(self.__number_of_hidden_messages(), '1')

    def test_writes_incomplete_fraud_event_to_audit_events_table_but_not_to_fraud_events_table(self):
        self.__setup_s3()
        with LogCapture('event-recorder', propagate=False) as log_capture:
            message_ids = self.__encrypt_and_send_to_sqs(
                [
                    create_fraud_event_without_idp_fraud_event_id_string('sample-id-1', 'session-id-1'),
                ]
            )

            event_handler.store_queued_events(None, None)

            self.__assert_audit_events_table_has_fraud_event_records([('sample-id-1', 'session-id-1', None)])
            self.__assert_billing_events_table_has_no_billing_event_records
            self.__assert_fraud_events_table_has_no_fraud_event_records
            log_capture.check(
                ('event-recorder', 'INFO', 'Got decryption key from S3'),
                ('event-recorder', 'INFO', 'Decrypted key successfully'),
                ('event-recorder', 'INFO', 'Created connection to DB'),
                ('event-recorder', 'INFO', 'Decrypted event with ID: sample-id-1'),
                ('event-recorder', 'INFO', 'Stored audit event: sample-id-1'),
                ('event-recorder', 'WARNING', 'Failed to store a fraud event [Event ID sample-id-1] due to key error'),
                ('event-recorder', 'ERROR',
                    'Failed to store event {0}, event type "{1}" from SQS message ID {2}'.format(
                        'sample-id-1', EVENT_TYPE, message_ids[0])),
                ('event-recorder', 'INFO', 'Queue is empty - finishing after 1 events')
            )
            self.assertEqual(self.__number_of_visible_messages(), '0')
            self.assertEqual(self.__number_of_hidden_messages(), '1')

    def test_does_not_delete_invalid_messages(self):
        self.__setup_s3()
        with LogCapture('event-recorder', propagate=False) as log_capture:
            message_ids = self.__encrypt_and_send_to_sqs(
                [
                    'invalid event',
                    create_event_string('sample-id-2', 'session-id-2'),
                ]
            )

            event_handler.store_queued_events(None, None)

            self.__assert_audit_events_table_has_billing_event_records(
                [('sample-id-2', 'session-id-2')], MINIMUM_LEVEL_OF_ASSURANCE)
            self.__assert_billing_events_table_has_billing_event_records([('session-id-2', 'sample-id-2')])
            self.__assert_fraud_events_table_has_no_fraud_event_records
            log_capture.check(
                ('event-recorder', 'INFO', 'Got decryption key from S3'),
                ('event-recorder', 'INFO', 'Decrypted key successfully'),
                ('event-recorder', 'INFO', 'Created connection to DB'),
                ('event-recorder', 'ERROR', 'Failed to decrypt message, SQS ID = {0}'.format(message_ids[0])),
                ('event-recorder', 'INFO', 'Decrypted event with ID: sample-id-2'),
                ('event-recorder', 'INFO', 'Stored audit event: sample-id-2'),
                ('event-recorder', 'INFO', 'Stored billing event: sample-id-2'),
                ('event-recorder', 'INFO', 'Deleted event from queue with ID: sample-id-2'),
                ('event-recorder', 'INFO', 'Queue is empty - finishing after 2 events')
            )
            self.assertEqual(self.__number_of_visible_messages(), '0')
            self.assertEqual(self.__number_of_hidden_messages(), '1')

    def test_event_handler_logs_event_to_stdout(self):
        self.__setup_s3()
        with OutputCapture() as output:
            events = [
                create_event_string('sample-id-1', 'session-id-1'),
                create_event_string('sample-id-1', 'session-id-1'),
            ]
            self.__encrypt_and_send_to_sqs(events)

            event_handler.store_queued_events(None, None)

            for event in events:
                self.assertIn(event, output.captured)

    def test_records_error_but_does_delete_messages_for_duplicate_events(self):
        self.__setup_s3()
        with LogCapture('event-recorder', propagate=False) as log_capture:
            self.__encrypt_and_send_to_sqs(
                [
                    create_event_string('sample-id-1', 'session-id-1'),
                    create_event_string('sample-id-1', 'session-id-1'),
                ]
            )

            event_handler.store_queued_events(None, None)

            self.__assert_audit_events_table_has_billing_event_records(
                [('sample-id-1', 'session-id-1')], MINIMUM_LEVEL_OF_ASSURANCE)
            self.__assert_billing_events_table_has_billing_event_records([('session-id-1', 'sample-id-1')])
            self.__assert_fraud_events_table_has_no_fraud_event_records
            log_capture.check(
                ('event-recorder', 'INFO', 'Got decryption key from S3'),
                ('event-recorder', 'INFO', 'Decrypted key successfully'),
                ('event-recorder', 'INFO', 'Created connection to DB'),
                ('event-recorder', 'INFO', 'Decrypted event with ID: sample-id-1'),
                ('event-recorder', 'INFO', 'Stored audit event: sample-id-1'),
                ('event-recorder', 'INFO', 'Stored billing event: sample-id-1'),
                ('event-recorder', 'INFO', 'Deleted event from queue with ID: sample-id-1'),
                ('event-recorder', 'INFO', 'Decrypted event with ID: sample-id-1'),
                ('event-recorder', 'WARNING',
                    'Failed to store an audit event. The Event ID sample-id-1 already exists in the database'),
                ('event-recorder', 'INFO', 'Stored audit event: sample-id-1'),
                ('event-recorder', 'WARNING',
                    'Failed to store a billing event. The Event ID sample-id-1 already exists in the database'),
                ('event-recorder', 'INFO', 'Stored billing event: sample-id-1'),
                ('event-recorder', 'INFO', 'Deleted event from queue with ID: sample-id-1'),
                ('event-recorder', 'INFO', 'Queue is empty - finishing after 2 events')
            )
            self.assertEqual(self.__number_of_visible_messages(), '0')
            self.assertEqual(self.__number_of_hidden_messages(), '0')

    def __encrypt_and_send_to_sqs(self, messages):
        message_ids = []
        for message in messages:
            encrypted_message = encrypt_string(message, ENCRYPTION_KEY)
            response = self.__sqs_client.send_message(
                QueueUrl=self.__queue_url,
                MessageBody=encrypted_message,
                DelaySeconds=0
            )
            message_ids.append(response['MessageId'])
        return message_ids

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

    def __assert_audit_events_table_has_billing_event_records(self, expected_events, minimum_level_of_assurance):
        for event in expected_events:
            with RunInTransaction(self.db_connection) as cursor:
                cursor.execute("""
                    SELECT
                        event_id,
                        time_stamp,
                        originating_service,
                        session_id,
                        event_type,
                        details->>'session_event_type',
                        details->>'pid',
                        details->>'request_id',
                        details->>'idp_entity_id',
                        details->>'transaction_entity_id',
                        details->>'minimum_level_of_assurance',
                        details->>'provided_level_of_assurance',
                        details->>'preferred_level_of_assurance'
                    FROM
                        audit.audit_events
                    WHERE
                        event_id = %s;
                """, [event[0]])
                matching_records = cursor.fetchone()

            self.assertIsNotNone(matching_records)
            self.assertEqual(matching_records[0], event[0])
            self.assertEqual(matching_records[1], datetime.fromtimestamp(TIMESTAMP / 1e3))
            self.assertEqual(matching_records[2], ORIGINATING_SERVICE)
            self.assertEqual(matching_records[3], event[1])
            self.assertEqual(matching_records[4], EVENT_TYPE)
            self.assertEqual(matching_records[5], SESSION_EVENT_TYPE)
            self.assertEqual(matching_records[6], PID)
            self.assertEqual(matching_records[7], REQUEST_ID)
            self.assertEqual(matching_records[8], IDP_ENTITY_ID)
            self.assertEqual(matching_records[9], TRANSACTION_ENTITY_ID)
            self.assertEqual(matching_records[10], minimum_level_of_assurance)
            self.assertEqual(matching_records[11], PROVIDED_LEVEL_OF_ASSURANCE)
            self.assertEqual(matching_records[12], PREFERRED_LEVEL_OF_ASSURANCE)

    def __assert_audit_events_table_has_fraud_event_records(self, expected_events):
        for event in expected_events:
            with RunInTransaction(self.db_connection) as cursor:
                cursor.execute("""
                    SELECT
                        event_id,
                        time_stamp,
                        originating_service,
                        session_id,
                        event_type,
                        details->>'session_event_type',
                        details->>'pid',
                        details->>'request_id',
                        details->>'idp_entity_id',
                        details->>'idp_fraud_event_id',
                        details->>'gpg45_status'
                    FROM
                        audit.audit_events
                    WHERE
                        event_id = %s;
                """, [event[0]])
                matching_records = cursor.fetchone()

            self.assertIsNotNone(matching_records)
            self.assertEqual(matching_records[0], event[0])
            self.assertEqual(matching_records[1], datetime.fromtimestamp(TIMESTAMP / 1e3))
            self.assertEqual(matching_records[2], ORIGINATING_SERVICE)
            self.assertEqual(matching_records[3], event[1])
            self.assertEqual(matching_records[4], EVENT_TYPE)
            self.assertEqual(matching_records[5], FRAUD_SESSION_EVENT_TYPE)
            self.assertEqual(matching_records[6], PID)
            self.assertEqual(matching_records[7], REQUEST_ID)
            self.assertEqual(matching_records[8], IDP_ENTITY_ID)
            self.assertEqual(matching_records[9], event[2])
            self.assertEqual(matching_records[10], GPG45_STATUS)

    def __assert_billing_events_table_has_no_billing_event_records(self):
        with RunInTransaction(self.db_connection) as cursor:
            cursor.execute("""
                SELECT
                    *
                FROM
                    billing.billing_events;
            """)
            matching_records = cursor.fetchone()

        self.assertIsNone(matching_records)

    def __assert_billing_events_table_has_billing_event_records(self, expected_ids):
        for (session_id, event_id) in expected_ids:
            with RunInTransaction(self.db_connection) as cursor:
                cursor.execute("""
                    SELECT
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
                    FROM
                        billing.billing_events
                    WHERE
                        session_id = %s;
                """, [session_id])
                matching_records = cursor.fetchone()

            self.assertIsNotNone(matching_records)
            self.assertEqual(matching_records[0], datetime.fromtimestamp(TIMESTAMP / 1e3))
            self.assertEqual(matching_records[1], session_id)
            self.assertEqual(matching_records[2], PID)
            self.assertEqual(matching_records[3], REQUEST_ID)
            self.assertEqual(matching_records[4], IDP_ENTITY_ID)
            self.assertEqual(matching_records[5], MINIMUM_LEVEL_OF_ASSURANCE)
            self.assertEqual(matching_records[6], PROVIDED_LEVEL_OF_ASSURANCE)
            self.assertEqual(matching_records[7], PREFERRED_LEVEL_OF_ASSURANCE)
            self.assertEqual(matching_records[8], event_id)
            self.assertEqual(matching_records[9], TRANSACTION_ENTITY_ID)

    def __assert_fraud_events_table_has_no_fraud_event_records(self):
        with RunInTransaction(self.db_connection) as cursor:
            cursor.execute("""
                SELECT
                    *
                FROM
                    billing.fraud_events;
            """)
            matching_records = cursor.fetchone()

        self.assertIsNone(matching_records)

    def __assert_fraud_events_table_has_fraud_event_records(self, expected_fraud_events):
        for fraud_event in expected_fraud_events:
            with RunInTransaction(self.db_connection) as cursor:
                cursor.execute("""
                    SELECT
                        time_stamp,
                        session_id,
                        hashed_persistent_id,
                        request_id,
                        entity_id,
                        fraud_event_id,
                        fraud_indicator,
                        transaction_entity_id
                    FROM
                        billing.fraud_events
                    WHERE
                        event_id = %s;
                """, [fraud_event[0]])
                matching_records = cursor.fetchone()

            self.assertIsNotNone(matching_records)
            self.assertEqual(matching_records[0], datetime.fromtimestamp(TIMESTAMP / 1e3))
            self.assertEqual(matching_records[1], fraud_event[1])
            self.assertEqual(matching_records[2], PID)
            self.assertEqual(matching_records[3], REQUEST_ID)
            self.assertEqual(matching_records[4], IDP_ENTITY_ID)
            self.assertEqual(matching_records[5], fraud_event[2])
            self.assertEqual(matching_records[6], GPG45_STATUS)
            self.assertEqual(matching_records[7], TRANSACTION_ENTITY_ID)

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
