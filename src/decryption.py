import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

__SALT_LENGTH = 16


def decrypt_message(base64_encrypted_message, decryption_key):
    """
    encrypted_message expects a string in the format "<16 character plaintext salt><AES CBC encrypted message>"
    """
    encrypted_message = base64.b64decode(base64_encrypted_message)
    salt = encrypted_message[:__SALT_LENGTH]
    cipher = Cipher(algorithms.AES(decryption_key), modes.CBC(salt), default_backend())
    decrypter = cipher.decryptor()
    message = encrypted_message[__SALT_LENGTH:]
    decrypted_message = decrypter.update(message) + decrypter.finalize()
    return __pkcs5_unpad(decrypted_message.decode('utf-8'))


def __pkcs5_unpad(message):
    """
    Expects a string padded in PKCS5 format
    See https://www.cryptosys.net/pki/manpki/pki_paddingschemes.html
    """
    final_character = message[-1]
    return message[0:-ord(final_character)]
