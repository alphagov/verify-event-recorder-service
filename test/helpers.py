import json
import os
import boto3
import botocore.exceptions
from src.database import RunInTransaction

EVENT_TYPE = 'session_event'
TIMESTAMP = 1518264452000  # '2018-02-10 12:07:32'
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


def clean_db(db_connection):
    with RunInTransaction(db_connection) as cursor:
        cursor.execute("""
            DELETE FROM idp_data.idp_fraud_event_contraindicators;
            DELETE FROM idp_data.idp_fraud_events;
            DELETE FROM idp_data.upload_session_validation_failures;
            DELETE FROM idp_data.upload_sessions;
            DELETE FROM billing.fraud_events;
            DELETE FROM billing.billing_events;
            DELETE FROM audit.audit_events;
        """)


def setup_stub_aws_config():
    os.environ = {
        'AWS_DEFAULT_REGION': 'eu-west-2',
        'AWS_ACCESS_KEY_ID': 'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY': 'AWS_SECRET_ACCESS_KEY'
    }


def create_event_string(event_id, session_id):
    return json.dumps({
        'eventId': event_id,
        'eventType': EVENT_TYPE,
        'timestamp': TIMESTAMP,
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
    })


def create_billing_event_without_minimum_level_of_assurance_string(event_id, session_id):
    return json.dumps({
        'eventId': event_id,
        'eventType': EVENT_TYPE,
        'timestamp': TIMESTAMP,
        'originatingService': ORIGINATING_SERVICE,
        'sessionId': session_id,
        'details': {
            'session_event_type': SESSION_EVENT_TYPE,
            'pid': PID,
            'request_id': REQUEST_ID,
            'idp_entity_id': IDP_ENTITY_ID,
            'transaction_entity_id': TRANSACTION_ENTITY_ID,
            'provided_level_of_assurance': PROVIDED_LEVEL_OF_ASSURANCE,
            'required_level_of_assurance': REQUIRED_LEVEL_OF_ASSURANCE
        }
    })


def create_fraud_event_string(event_id, session_id, fraud_event_id):
    return json.dumps({
        'eventId': event_id,
        'eventType': EVENT_TYPE,
        'timestamp': TIMESTAMP,
        'originatingService': ORIGINATING_SERVICE,
        'sessionId': session_id,
        'details': {
            'session_event_type': FRAUD_SESSION_EVENT_TYPE,
            'pid': PID,
            'request_id': REQUEST_ID,
            'idp_entity_id': IDP_ENTITY_ID,
            'idp_fraud_event_id': fraud_event_id,
            'gpg45_status': GPG45_STATUS,
            'transaction_entity_id': TRANSACTION_ENTITY_ID
        }
    })


def create_fraud_event_without_idp_fraud_event_id_string(event_id, session_id):
    return json.dumps({
        'eventId': event_id,
        'eventType': EVENT_TYPE,
        'timestamp': TIMESTAMP,
        'originatingService': ORIGINATING_SERVICE,
        'sessionId': session_id,
        'details': {
            'session_event_type': FRAUD_SESSION_EVENT_TYPE,
            'pid': PID,
            'request_id': REQUEST_ID,
            'idp_entity_id': IDP_ENTITY_ID,
            'gpg45_status': GPG45_STATUS,
            'transaction_entity_id': TRANSACTION_ENTITY_ID
        }
    })


def file_exists_in_s3(bucket_name, key):
    s3 = boto3.resource('s3')
    try:
        s3.Object(bucket_name, key).load()
        return True
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            return False
        else:
            raise
