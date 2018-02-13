import unittest
from src import service_handler

class TestStringMethods(unittest.TestCase):

    def test(self):
        service_handler.hello_world()