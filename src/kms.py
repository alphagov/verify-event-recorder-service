import boto3
import base64

def decrypt(encrypted_key):
    kms_client = boto3.client('kms')
    binary_data = base64.b64decode(encrypted_key)
    response = kms_client.decrypt(CiphertextBlob=binary_data)
    return response['Plaintext']