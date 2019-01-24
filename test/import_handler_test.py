import os
import boto3
import base64
import json
import psycopg2

from moto import mock_s3, mock_kms
from unittest import TestCase
from datetime import datetime
from testfixtures import LogCapture
from retrying import retry

from src import import_handler
from src.database import RunInTransaction

EVENT_TYPE = 'session_event'
TIMESTAMP = 1518264000000
ISO3359_TIMESTAMP = '2018-02-10T12:00:00Z'
ORIGINATING_SERVICE = 'test service'
ENCRYPTION_KEY = b'sixteen byte key'
DB_PASSWORD = 'secretPassword'
SESSION_EVENT_TYPE = 'idp_authn_succeeded'
PID = '26b1e565bb63e7fc3c2ccf4e018f50b84953b02b89d523654034e24a4907d50c'
REQUEST_ID = '_a217717d-ce3d-407c-88c1-d3d592b6db8c'
IDP_ENTITY_ID = 'idp entity id'
TRANSACTION_ENTITY_ID = 'transaction entity id'
MINIMUM_LEVEL_OF_ASSURANCE = 'LEVEL_2'
PROVIDED_LEVEL_OF_ASSURANCE = 'LEVEL_2'
REQUIRED_LEVEL_OF_ASSURANCE = 'LEVEL_2'
FRAUD_SESSION_EVENT_TYPE = 'fraud_detected'
GPG45_STATUS = 'AA01'
IMPORT_BUCKET_NAME = 's3-import-bucket'
IMPORT_FILE_NAME = 'imports/replay-events.json'


@mock_s3
@mock_kms
class ImportHandlerTest(TestCase):
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
        self.__setup_stub_aws_config()
        self.__setup_kms()
        self.__setup_db_connection_string()

    def tearDown(self):
        self.__clean_db()

    def test_writes_messages_to_db_with_password_from_env(self):
        self.__setup_s3()
        self.__setup_db_connection_string(True)

        self.__write_import_file_to_s3(
            [
                self.__create_event_string('sample-id-1', 'session-id-1'),
                self.__create_event_string('sample-id-2', 'session-id-2'),
                self.__create_fraud_event_string('sample-id-3', 'session-id-3', 'fraud-event-id-1'),
                self.__create_fraud_event_string('sample-id-4', 'session-id-4', 'fraud-event-id-2'),
            ]
        )

        import_handler.import_events(self.__create_s3_event(), None)

        self.__assert_audit_events_table_has_billing_event_records([('sample-id-1', 'session-id-1'), ('sample-id-2', 'session-id-2')], MINIMUM_LEVEL_OF_ASSURANCE)
        self.__assert_audit_events_table_has_fraud_event_records([('sample-id-3', 'session-id-3', 'fraud-event-id-1'), ('sample-id-4', 'session-id-4', 'fraud-event-id-2')])
        self.__assert_billing_events_table_has_billing_event_records(['session-id-1', 'session-id-2'])
        self.__assert_fraud_events_table_has_fraud_event_records([('session-id-3', 'fraud-event-id-1'), ('session-id-4', 'fraud-event-id-2')])
        self.__assert_import_file_has_been_removed_from_s3()

    def test_does_not_write_dupicate_messages_to_db_with_password_from_env(self):
        self.__setup_s3()
        self.__setup_db_connection_string(True)

        self.__write_import_file_to_s3(
            [
                self.__create_event_string('sample-id-1', 'session-id-1'),
                self.__create_event_string('sample-id-1', 'session-id-1'),
                self.__create_fraud_event_string('sample-id-3', 'session-id-3', 'fraud-event-id-1'),
                self.__create_fraud_event_string('sample-id-3', 'session-id-3', 'fraud-event-id-1'),
            ]
        )

        with LogCapture('event-recorder', propagate=False) as log_capture:
            import_handler.import_events(self.__create_s3_event(), None)

            self.__assert_audit_events_table_has_billing_event_records([('sample-id-1', 'session-id-1')], MINIMUM_LEVEL_OF_ASSURANCE)
            self.__assert_audit_events_table_has_fraud_event_records([('sample-id-3', 'session-id-3', 'fraud-event-id-1')])
            self.__assert_billing_events_table_has_billing_event_records(['session-id-1'])
            self.__assert_fraud_events_table_has_fraud_event_records([('session-id-3', 'fraud-event-id-1')])
            log_capture.check(
                (
                    'event-recorder',
                    'WARNING',
                    'Failed to store an audit event. The Event ID sample-id-1 already exists in the database'
                ),
                (
                    'event-recorder',
                    'WARNING',
                    'Failed to store an audit event. The Event ID sample-id-3 already exists in the database'
                )
            )
            self.__assert_import_file_has_been_removed_from_s3()

    def __clean_db(self):
        with RunInTransaction(self.db_connection) as cursor:
            cursor.execute("""
                DELETE FROM audit.audit_events;
                DELETE FROM billing.billing_events;
                DELETE FROM billing.fraud_events;
            """)

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
                        details->>'required_level_of_assurance'
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
            self.assertEqual(matching_records[12], REQUIRED_LEVEL_OF_ASSURANCE)

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

    def __assert_billing_events_table_has_billing_event_records(self, expected_session_ids):
        for session_id in expected_session_ids:
            with RunInTransaction(self.db_connection) as cursor:
                cursor.execute("""
                    SELECT
                        time_stamp,
                        session_id,
                        hashed_persistent_id,
                        request_id,
                        idp_entity_id,
                        minimum_level_of_assurance,
                        required_level_of_assurance,
                        provided_level_of_assurance
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
            self.assertEqual(matching_records[7], REQUIRED_LEVEL_OF_ASSURANCE)

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
                        fraud_indicator
                    FROM
                        billing.fraud_events
                    WHERE
                        session_id = %s;
                """, [fraud_event[0]])
                matching_records = cursor.fetchone()

            self.assertIsNotNone(matching_records)
            self.assertEqual(matching_records[0], datetime.fromtimestamp(TIMESTAMP / 1e3))
            self.assertEqual(matching_records[1], fraud_event[0])
            self.assertEqual(matching_records[2], PID)
            self.assertEqual(matching_records[3], REQUEST_ID)
            self.assertEqual(matching_records[4], IDP_ENTITY_ID)
            self.assertEqual(matching_records[5], fraud_event[1])
            self.assertEqual(matching_records[6], GPG45_STATUS)

    def __assert_import_file_has_been_removed_from_s3(self):
        s3 = boto3.resource('s3')
        bucket = s3.Bucket(IMPORT_BUCKET_NAME)
        self.assertEqual(len(list(bucket.objects.all())), 0)

    def __setup_db_connection_string(self, password_in_env=False):
        if password_in_env:
          os.environ['DB_CONNECTION_STRING'] = self.db_connection_string
          os.environ['ENCRYPTED_DATABASE_PASSWORD'] = self.__encrypt(DB_PASSWORD)
        else:
          os.environ['DB_CONNECTION_STRING'] = "{} password='{}'".format(self.db_connection_string, DB_PASSWORD)

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
        self.__s3_client.create_bucket(
            Bucket=IMPORT_BUCKET_NAME,
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
        self.__write_to_s3(bucket_name, filename, encrypted_encryption_key)
        os.environ['DECRYPTION_KEY_BUCKET_NAME'] = bucket_name
        os.environ['DECRYPTION_KEY_FILE_NAME'] = filename

    def __write_import_file_to_s3(self, messages):
        self.__write_to_s3(IMPORT_BUCKET_NAME, IMPORT_FILE_NAME, '\n'.join(messages))

    def __write_to_s3(self, bucket_name, filename, content):
        self.__s3_client.put_object(
            Bucket=bucket_name,
            Key=filename,
            Body=content
        )

    def __setup_stub_aws_config(self):
        os.environ = {
            'AWS_DEFAULT_REGION': 'eu-west-2',
            'AWS_ACCESS_KEY_ID': 'AWS_ACCESS_KEY_ID',
            'AWS_SECRET_ACCESS_KEY': 'AWS_SECRET_ACCESS_KEY'
        }

    def __create_event_string(self, event_id, session_id):
        return json.dumps({
            '_id': {
                '$oid': event_id
            },
            'document': {
                'eventId': event_id,
                'eventType': EVENT_TYPE,
                'timestamp': ISO3359_TIMESTAMP,
                'originatingService': ORIGINATING_SERVICE,
                'sessionId': session_id,
                'details': {
                    'session_event_type': SESSION_EVENT_TYPE,
                    'pid': PID,
                    'request_id': REQUEST_ID,
                    'idp_entity_id': IDP_ENTITY_ID,
                    'transaction_entity_id': TRANSACTION_ENTITY_ID,
                    'minimum_level_of_assurance': MINIMUM_LEVEL_OF_ASSURANCE,
                    'provided_level_of_assurance': PROVIDED_LEVEL_OF_ASSURANCE,
                    'required_level_of_assurance': REQUIRED_LEVEL_OF_ASSURANCE
                }
            }
        })

    def __create_fraud_event_string(self, event_id, session_id, fraud_event_id):
        return json.dumps({
            '_id': {
                '$oid': event_id
            },
            'document': {
                'eventId': event_id,
                'eventType': EVENT_TYPE,
                'timestamp': ISO3359_TIMESTAMP,
                'originatingService': ORIGINATING_SERVICE,
                'sessionId': session_id,
                'details': {
                    'session_event_type': FRAUD_SESSION_EVENT_TYPE,
                    'pid': PID,
                    'request_id': REQUEST_ID,
                    'idp_entity_id': IDP_ENTITY_ID,
                    'idp_fraud_event_id': fraud_event_id,
                    'gpg45_status': GPG45_STATUS
                }
            }
        })

    def __create_s3_event(self):
        return {
          "Records": [
            {
              "s3": {
                "bucket": {
                  "name": IMPORT_BUCKET_NAME,
                },
                "object": {
                  "key": IMPORT_FILE_NAME,
                }
              }
            }
          ]
        }
