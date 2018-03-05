from unittest import TestCase
from src.decryption import decrypt_message
from test.test_encrypter import encrypt_string


class EventHandlerTest(TestCase):
    __key = 'sixteen byte key'

    def test_decrypts_message_with_full_final_block_padding(self):
        # PKCS5 Padding uses a block of chr(0) to indicate that there was a full
        # block of bytes in the previous block
        sixteen_char_message_with_padding = '{ abcdefghijkl }' + chr(16)*16
        encrypted_message = encrypt_string(sixteen_char_message_with_padding, self.__key)

        decrypted_message = decrypt_message(encrypted_message, self.__key)

        self.assertEqual(decrypted_message, '{ abcdefghijkl }')

    def test_decrypts_message_with_some_padding(self):
        sixteen_char_message = '{ abcdefghij }' + chr(2)*2
        encrypted_message = encrypt_string(sixteen_char_message, self.__key)

        decrypted_message = decrypt_message(encrypted_message, self.__key)

        self.assertEqual(decrypted_message, '{ abcdefghij }')

    def test_decrypts_message_with_more_than_ten_padded_characters(self):
        sixteen_char_message = '{ a }' + chr(11)*11
        encrypted_message = encrypt_string(sixteen_char_message, self.__key)

        decrypted_message = decrypt_message(encrypted_message, self.__key)

        self.assertEqual(decrypted_message, '{ a }')
