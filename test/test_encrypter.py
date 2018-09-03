import base64
from uuid import uuid4
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# padding from https://github.com/dlitz/pycrypto/blob/master/lib/Crypto/Util/Padding.py - in PyCrypto 2.7a1

def pad(data_to_pad, block_size, style='pkcs7'):
    padding_len = block_size-len(data_to_pad)%block_size
    if style == 'pkcs7':
        padding = chr(padding_len)*padding_len
    elif style == 'x923':
        padding = chr(0)*(padding_len-1) + chr(padding_len)
    elif style == 'iso7816':
        padding = chr(128) + chr(0)*(padding_len-1)
    else:
        raise ValueError("Unknown padding style")
    return data_to_pad + padding

def encrypt_string(plaintext, encryption_key):
    salt = str(uuid4())[:16]
    cipher = Cipher(algorithms.AES(encryption_key), modes.CBC(salt.encode()), backend=default_backend())
    encryptor = cipher.encryptor()
    encrypted = encryptor.update(pad(plaintext, 128).encode()) + encryptor.finalize()
    return base64.b64encode(bytes(salt, 'utf-8') + encrypted).decode('utf-8')
