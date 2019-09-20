import boto3
import os


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

    s3_client.copy_object(Bucket=bucket_name, CopySource=f'{bucket_name}/{filename}', Key=f'{new_prefix}/{new_filename}')
    s3_client.delete_object(Bucket=bucket_name, Key=filename)
