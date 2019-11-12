import os
import tempfile

import boto3


def fetch_decryption_key():
    s3_client = boto3.client('s3')
    bucket_name = os.environ['DECRYPTION_KEY_BUCKET_NAME']
    filename = os.environ['DECRYPTION_KEY_FILE_NAME']
    response = s3_client.get_object(Bucket=bucket_name, Key=filename)
    return response['Body'].read()


def fetch_import_file(bucket_name, filename):
    s3_client = boto3.client('s3')
    response = s3_client.get_object(Bucket=bucket_name, Key=filename)
    return response['Body'].iter_lines()


def download_import_file(bucket_name, filename):
    s3_client = boto3.client('s3')
    fd, temp_file_name = tempfile.mkstemp()
    with open(temp_file_name, 'wb') as data:
        s3_client.download_fileobj(bucket_name, filename, data)

    os.close(fd)
    return temp_file_name


def delete_import_file(bucket_name, filename):
    s3_client = boto3.client('s3')
    s3_client.delete_object(Bucket=bucket_name, Key=filename)


def fetch_object_tags(bucket_name, filename):
    s3_client = boto3.client('s3')
    response = s3_client.get_object_tagging(Bucket=bucket_name, Key=filename)
    return {tag['Key']: tag['Value'] for tag in response['TagSet']}


def move_file(bucket_name, filename, new_prefix):
    s3_client = boto3.client('s3')
    new_filename = os.path.basename(filename)

    s3_client.copy_object(Bucket=bucket_name,
                          CopySource=f'{bucket_name}/{filename}',
                          Key=f'{new_prefix}/{new_filename}',
                          TaggingDirective="COPY",
                          ServerSideEncryption="AES256")
    s3_client.delete_object(Bucket=bucket_name, Key=filename)
