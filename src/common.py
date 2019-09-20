import os
import boto3

from src.kms import decrypt
from psycopg2.extensions import parse_dsn


def get_database_password(dsn):
    if 'ENCRYPTED_DATABASE_PASSWORD' in os.environ:
        # boto returns decrypted as b'bytes' so decode to convert to password string
        return decrypt(os.environ['ENCRYPTED_DATABASE_PASSWORD']).decode()
    else:
        dsn_components = parse_dsn(dsn)
        return boto3.client('rds').generate_db_auth_token(dsn_components['host'], 5432, dsn_components['user'])
