from unittest import TestCase
from src.decryption import decrypt_message
from test.test_encrypter import encrypt_string


class EventHandlerTest(TestCase):
    __key = 'sixteen byte key'

    def test_decrypts_message_with_full_final_block_padding(self):
        sixteen_char_message = '{ abcdefghijkl }'
        encrypted_message = encrypt_string(sixteen_char_message, self.__key)

        decrypted_message = decrypt_message(encrypted_message, self.__key)

        self.assertEqual(decrypted_message, '{ abcdefghijkl }')

    def test_decrypts_message_with_some_padding(self):
        fourteen_char_message = '{ abcdefghij }'
        encrypted_message = encrypt_string(fourteen_char_message, self.__key)

        decrypted_message = decrypt_message(encrypted_message, self.__key)

        self.assertEqual(decrypted_message, '{ abcdefghij }')

    def test_decrypts_message_with_more_than_ten_padded_characters(self):
        five_char_message = '{ a }'
        encrypted_message = encrypt_string(five_char_message, self.__key)

        decrypted_message = decrypt_message(encrypted_message, self.__key)

        self.assertEqual(decrypted_message, '{ a }')
