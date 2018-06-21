import base64
from Crypto.Cipher import AES

__SALT_LENGTH = 16


def decrypt_message(base64_encrypted_message, decryption_key):
    """
    encrypted_message expects a string in the format "<16 character plaintext salt><AES CBC encrypted message>"
    """
    encrypted_message = base64.b64decode(base64_encrypted_message)
    salt = encrypted_message[:__SALT_LENGTH]
    cipher = AES.new(decryption_key, AES.MODE_CBC, IV=salt)
    message = encrypted_message[__SALT_LENGTH:]
    return __pkcs5_unpad(cipher.decrypt(message).decode('utf-8'))


def __pkcs5_unpad(message):
    """
    Expects a string padded in PKCS5 format
    See https://www.cryptosys.net/pki/manpki/pki_paddingschemes.html
    """
    final_character = message[-1]
    return message[0:-ord(final_character)]
