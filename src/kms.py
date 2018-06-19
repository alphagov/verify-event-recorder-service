import boto3

def decrypt(encrypted_key):
    kms_client = boto3.client('kms')
    response = kms_client.decrypt(CiphertextBlob=encrypted_key)
    return response['Plaintext']