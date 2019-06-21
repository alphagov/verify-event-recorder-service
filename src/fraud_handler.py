import os
import logging
import json
import boto3
from datetime import datetime
from botocore.errorfactory import ClientError
import random
import string


class VerifyFraudToS3:


    def __init__(
        self,
        key,
        bucket,
        role,
        s_index,
        s_sourcetype="json",
        s_source="null",
        s_host="null"
        ):

        self.key = key
        self.bucket = bucket
        self.role = role
        self.s_index = s_index
        self.s_sourcetype = s_sourcetype
        self.s_source = s_source
        self.s_host = s_host


    def base_json_event(self):
        return {
            "host": self.s_host,
            "source": self.s_source,
            "sourcetype": self.s_sourcetype,
            "index": self.s_index,
            "event": {},
            }


    def aws_session(self, role, session_name='session_verify_fraud_logging'):
        logger = logging.getLogger('assume-role')
        logger.setLevel(logging.INFO)

        try:
            client = boto3.client('sts')
            response = client.assume_role(RoleArn=self.role, RoleSessionName=session_name)
            session = boto3.Session(
                aws_access_key_id=response['Credentials']['AccessKeyId'],
                aws_secret_access_key=response['Credentials']['SecretAccessKey'],
                aws_session_token=response['Credentials']['SessionToken'])
            return session
        except ClientError as e:
            logger.error('Unable to assume a session. {0}'.format(e))
            raise e

    def push_to_s3(self, payload):
        logger = logging.getLogger('push-to-s3')
        logger.setLevel(logging.INFO)

        session_assumed = self.aws_session(self.role)
        logger.info(session_assumed.client('sts').get_caller_identity()['Account'])

        s3 = session_assumed.resource('s3')

        if isinstance(payload, str):
            payload = json.loads(payload)
        json_event = self.base_json_event()

        if "timestamp" in payload:
            json_event["time"] = payload["timestamp"]

        json_event["event"] = json.dumps(payload)
        event = str(json.dumps(json_event))

        try:
            s3.Object(self.bucket, self.key).put(
                    Body=(bytes(json.dumps(event, indent=2).encode('UTF-8')))
                )
        except ClientError as e:
            logger.error('Unable to write to S3 bucket. {0}'.format(e))
            raise e


def fraud_logging_handler(event, context):

    bucket = os.environ['SPLUNK_VERIFY_FRAUD_S3_NAME']
    role = os.environ['SPLUNK_S3_BUCKET_ROLE']
    s_index = os.environ['SPLUNK_INDEX']
    today = str(datetime.now())
    letters = string.ascii_lowercase
    random_string = ''.join(random.choice(letters) for i in range(8))
    key = 'verify-fraud-events-{}-{}.log'.format(random_string, today)


    verify_to_s3 = VerifyFraudToS3(
        key,
        bucket,
        role,
        s_index,
    )
    return verify_to_s3.push_to_s3(event)

