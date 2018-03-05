import base64
import boto3
import os
from Crypto.Cipher import AES

__SALT_LENGTH = 16


def fetch_decryption_key():
    encrypted_key = __fetch_encrypted_key()
    return __decrypt_key(encrypted_key)


def decrypt_message(encrypted_message, decryption_key):
    """
    encrypted_message expects a string in the format "<16 character plaintext salt><AES CBC encrypted message>"
    """
    salt = encrypted_message[:__SALT_LENGTH]
    cipher = AES.new(decryption_key, AES.MODE_CBC, IV=salt)
    message = base64.b64decode(encrypted_message[__SALT_LENGTH:])
    return __pkcs5_unpad(cipher.decrypt(message).decode('utf-8'))


def __pkcs5_unpad(message):
    """
    Expects a string padded in PKCS5 format
    See https://www.cryptosys.net/pki/manpki/pki_paddingschemes.html
    """
    final_character = message[-1]
    return message[0:-ord(final_character)]


def __fetch_encrypted_key():
    s3_client = boto3.client('s3')
    bucket_name = os.environ['DECRYPTION_KEY_BUCKET_NAME']
    filename = os.environ['DECRYPTION_KEY_FILE_NAME']
    response = s3_client.get_object(Bucket=bucket_name, Key=filename)
    return response['Body'].read()


def __decrypt_key(encrypted_key):
    kms_client = boto3.client('kms')
    return kms_client.decrypt(CiphertextBlob=encrypted_key)['Plaintext'].decode('utf-8')

