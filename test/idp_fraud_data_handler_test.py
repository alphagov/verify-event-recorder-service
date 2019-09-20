import os
import boto3
import psycopg2
import urllib.parse
import uuid

from moto import mock_s3
from unittest import TestCase
from datetime import datetime
from testfixtures import LogCapture
from retrying import retry

from src import idp_fraud_data_handler
from src.idp_fraud_event import IdpFraudEvent
from src.database import RunInTransaction

IMPORT_BUCKET_NAME = 's3-idp-fraud-data-bucket'
IMPORT_FILE_NAME = 'idp-data.csv'
UPLOAD_USERNAME = 'my.user.name@example.com'
VALID_ENTITY_ID = 'http://my.example.com/idp/SAML'
DB_PASSWORD = 'secretPassword'


@mock_s3
class IdpFraudDataHandlerTest(TestCase):
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
        self.__setup_stub_aws_config()
        self.__setup_s3()
        self.__setup_db_connection_string()

    def tearDown(self):
        self.__clean_db()

    def test_writes_messages_to_db(self):
        idp_fraud_events = [
            IdpFraudEvent(
                timestamp="05/08/2019 11:54",
                idp_event_id="1111111",
                idp_entity_id=VALID_ENTITY_ID,
                fid_code="DF01",
                contra_indicators=["A04", "D02"],
                contra_score=-5,
                request_id="_{}".format(uuid.uuid4()),
                client_ip_address="111.222.222.111",
                pid=uuid.uuid4()
            ),
            IdpFraudEvent(
                timestamp="07/08/2019 16:37",
                idp_event_id="2222222",
                idp_entity_id=VALID_ENTITY_ID,
                fid_code="DF01",
                contra_indicators=["ROLB", "D15"],
                contra_score=-5,
                request_id="_{}".format(uuid.uuid4()),
                client_ip_address="222.111.111.222",
                pid=uuid.uuid4()
            ),
            IdpFraudEvent(
                timestamp="10/08/2019 09:24",
                idp_event_id="3333333",
                idp_entity_id=VALID_ENTITY_ID,
                fid_code="DF01",
                contra_indicators=["A01", "A05", "V03"],
                contra_score=-10,
                request_id="_{}".format(uuid.uuid4()),
                client_ip_address="111.111.111.111",
                pid=uuid.uuid4()
            ),
            IdpFraudEvent(
                timestamp="23/08/2019 21:22",
                idp_event_id="4444444",
                idp_entity_id=VALID_ENTITY_ID,
                fid_code="DF01",
                contra_indicators=["D02"],
                contra_score=-4,
                request_id="_{}".format(uuid.uuid4()),
                client_ip_address="222.222.222.222",
                pid=uuid.uuid4()
            ),
        ]
        self.__write_import_file_to_s3(idp_fraud_events)

        with LogCapture('idp_fraud_data_handler', propagate=False) as log_capture:
            idp_fraud_data_handler.idp_fraud_data_events(self.__create_s3_event(), None)

            log_capture.check(
                (
                    'idp_fraud_data_handler',
                    'INFO',
                    'Created connection to DB'
                ),
            )
            self.__assert_upload_session_exists_in_database(False)
            self.__assert_import_file_has_been_removed_from_s3()

    def __clean_db(self):
        with RunInTransaction(self.db_connection) as cursor:
            cursor.execute("""
                DELETE FROM idp_data.idp_fraud_event_contraindicators;
                DELETE FROM idp_data.idp_fraud_events;
                DELETE FROM idp_data.upload_session_validation_failures;
                DELETE FROM idp_data.upload_sessions;
            """)

    def __assert_import_file_has_been_removed_from_s3(self):
        s3 = boto3.resource('s3')
        bucket = s3.Bucket(IMPORT_BUCKET_NAME)
        self.assertEqual(len(list(bucket.objects.all())), 0)

    def __assert_upload_session_exists_in_database(self, passed_validation):
        with RunInTransaction(self.db_connection) as cursor:
            cursor.execute("""
                SELECT 
                    id,
                    source_file_name,
                    idp_entity_id,
                    userid,
                    passed_validation
                  FROM idp_data.upload_sessions
            """)
            result = cursor.fetchone()

        self.assertIsNotNone(result)
        self.assertIsNotNone(result[0])
        self.assertEqual(result[1], IMPORT_FILE_NAME)
        self.assertEqual(result[2], VALID_ENTITY_ID)
        self.assertEqual(result[3], UPLOAD_USERNAME)
        self.assertEqual(result[4], passed_validation)

    def __setup_db_connection_string(self):
        os.environ['DB_CONNECTION_STRING'] = "{} password='{}'".format(self.db_connection_string, DB_PASSWORD)

    def __setup_s3(self):
        self.__s3_client = boto3.client('s3')
        self.__s3_client.create_bucket(
            Bucket=IMPORT_BUCKET_NAME,
        )

    def __write_import_file_to_s3(self, idp_fraud_events):
        rows = ['FID_Event_Time, EVENT_ID, FID_code, contraindicators_raised, Contra_score, Authentication_ID, Client_IPAddress, PID']
        rows = rows + [self.__idp_fraud_event_to_csv_string(event) for event in idp_fraud_events]
        self.__write_to_s3(IMPORT_BUCKET_NAME, IMPORT_FILE_NAME, '\n'.join(rows))

    def __write_to_s3(self, bucket_name, filename, content):
        tags = {
            'username': UPLOAD_USERNAME,
            'idp': VALID_ENTITY_ID,
        }
        self.__s3_client.put_object(
            Bucket=bucket_name,
            Key=filename,
            Body=content,
            Tagging=urllib.parse.urlencode(tags)
        )

    def __setup_stub_aws_config(self):
        os.environ = {
            'AWS_DEFAULT_REGION': 'eu-west-2',
            'AWS_ACCESS_KEY_ID': 'AWS_ACCESS_KEY_ID',
            'AWS_SECRET_ACCESS_KEY': 'AWS_SECRET_ACCESS_KEY'
        }

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

    def __idp_fraud_event_to_csv_string(self, idp_fraud_event):
        return '"{}","{}","{}","{}",{},"{}","{}","{}"'.format(
            idp_fraud_event.timestamp,
            idp_fraud_event.idp_event_id,
            idp_fraud_event.fid_code,
            ','.join(idp_fraud_event.contra_indicators),
            idp_fraud_event.contra_score,
            idp_fraud_event.request_id,
            idp_fraud_event.client_ip_address,
            idp_fraud_event.pid
        )
