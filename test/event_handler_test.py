import unittest
import os
import boto3
import io
from moto import mock_sqs
from unittest.mock import patch

from src import event_handler


def mock_get_request(url):
    print(url)


class EventHandlerTest(unittest.TestCase):

    @mock_sqs
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_reads_messages_from_queue(self, mock_stdout):
        self.__setup_stub_aws_config()
        queue = self.__create_queue_with_messages(['sample event 1', 'sample event 2'])
        self.__add_queue_url_to_environment_variables(queue['QueueUrl'])

        event_handler.store_queued_events(None, None)

        self.assertEqual(mock_stdout.getvalue(), 'sample event 1\nsample event 2\n')

    def __setup_stub_aws_config(self):
        os.environ = {
            'AWS_DEFAULT_REGION': 'eu-west-2',
        }

    def __create_queue_with_messages(self, messages):
        sqs_client = boto3.client('sqs')
        queue = sqs_client.create_queue(
            QueueName='test-queue'
        )
        for message in messages:
            sqs_client.send_message(
                QueueUrl=queue['QueueUrl'],
                MessageBody=message,
                DelaySeconds=0
            )
        return queue

    def __add_queue_url_to_environment_variables(self, queue_url):
        os.environ['QUEUE_URL'] = queue_url


class MockResponse(object):
    def __init__(self, body, response_code):
        self.body = body,
        self.response_code = response_code
