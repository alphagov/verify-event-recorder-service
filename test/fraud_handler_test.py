import os
import boto3
import json
import datetime
import string
import random

from moto import mock_s3, mock_sts
from unittest import TestCase
from testfixtures import LogCapture
from retrying import retry
from src import fraud_handler


S_INDEX = 'fraud-test-index'
TODAY = str(datetime.datetime.now())
LETTERS = string.ascii_lowercase
RANDOM_STRING = ''.join(random.choice(LETTERS) for i in range(8))
KEY = 'verify-fraud-events-{}-{}.log'.format(RANDOM_STRING, TODAY)
BUCKET = 'key-bucket'
ROLE = 'arn:partition:service:region:account-id:resource'

EVENT_TYPE = 'session_event'
ISO3359_TIMESTAMP = '2018-02-10T12:00:00Z'
ORIGINATING_SERVICE = 'test service'
PID = '26b1e565bb63e7fc3c2ccf4e018f50b84953b02b89d523654034e24a4907d50c'
REQUEST_ID = '_a217717d-ce3d-407c-88c1-d3d592b6db8c'
IDP_ENTITY_ID = 'idp entity id'
TRANSACTION_ENTITY_ID = 'transaction entity id'
FRAUD_SESSION_EVENT_TYPE = 'fraud_detected'
GPG45_STATUS = 'AA01'


@mock_s3
@mock_sts
class FraudHandlerTest(TestCase):
    __s3_client = None
    __sts_client = None

    def setUp(self):
        self.__setup_stub_aws_config()

    def __setup_s3(self):
        self.__s3_client = boto3.client('s3')
        self.__s3_client.create_bucket(
            Bucket=BUCKET,
        )

    def __setup_sts(self):
        self.__sts_client = boto3.client('sts')
        self.__sts_client.assume_role(RoleArn=ROLE, RoleSessionName='Test-assume')

    def __create_fraud_event_string(self, event_id, session_id, fraud_event_id):
        CONTENT = json.dumps({
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
        return CONTENT


    def __write_to_s3(self, BUCKET, KEY):
        CONTENT = self.__create_fraud_event_string('sample-id-3', 'session-id-3', 'fraud-event-id-1')
        self.__s3_client.put_object(
            Bucket=BUCKET,
            Key=KEY,
            Body=CONTENT
        )


    def __setup_stub_aws_config(self):
        os.environ = {
            'AWS_DEFAULT_REGION': 'eu-west-2',
            'AWS_ACCESS_KEY_ID': 'AWS_ACCESS_KEY_ID',
            'AWS_SECRET_ACCESS_KEY': 'AWS_SECRET_ACCESS_KEY'
        }

    def test_push_to_s3(self):
        self.__setup_s3()
        self.__setup_sts()
        self.__write_to_s3(BUCKET, KEY)
        self.key = KEY
        self.bucket = BUCKET
        self.role = ROLE
        self.s_index = S_INDEX
        self.verify_to_s3 = fraud_handler.VerifyFraudToS3(
            self.key,
            self.bucket,
            self.role,
            self.s_index,
        )
        self.verify_to_s3.push_to_s3(None)
