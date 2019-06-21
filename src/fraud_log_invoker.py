import json
import boto3

def send_to_fraud_logger(event):
  lambda_client = boto3.client('lambda')
  lambda_client.invoke(FunctionName='fraud_handler',
  InvocationType='Event',
  Payload=json.dumps(event),
  )
