import base64
from uuid import uuid4
from Crypto.Cipher import AES


def encrypt_string(plaintext, encryption_key):
    salt = str(uuid4())[:16]
    cipher = AES.new(encryption_key, AES.MODE_CBC, IV=salt)
    encrypted = cipher.encrypt(plaintext)
    return salt + base64.b64encode(encrypted).decode('utf-8')