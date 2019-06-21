import json
import boto3
from datetime import datetime

def convert_to_json(event):
    return {
        'time_stamp': str(datetime.fromtimestamp(int(event.timestamp) / 1e3)),
        'session_id': event.session_id,
        'hashed_persistent_id': event.details['pid'],
        'request_id': event.details['request_id'],
        'entity_id': event.details['idp_entity_id'],
        'fraud_event_id': event.details['idp_fraud_event_id'],
        'fraud_indicator': event.details['gpg45_status']
    }

def send_to_fraud_logger(event):
    lambda_client = boto3.client('lambda')
    lambda_client.invoke(FunctionName='fraud_handler',
    InvocationType='Event',
    Payload=json.dumps(convert_to_json(event)),
    )
