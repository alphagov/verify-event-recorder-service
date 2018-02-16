import os
import boto3
import io
import json
import uuid
from moto import mock_sqs
from unittest import TestCase
from unittest.mock import patch

from src import event_handler


@mock_sqs
class EventHandlerTest(TestCase):

    def setUp(self):
        setup_stub_aws_config()
        self.__sqs_client = boto3.client('sqs')
        self.__queue_url = create_queue(self.__sqs_client)
        add_queue_url_to_environment_variables(self.__queue_url)

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_reads_messages_from_queue(self, mock_stdout):
        self.__send_messages_to_queue(
            [
                create_event_string('sample-id-1'),
                create_event_string('sample-id-2'),
            ]
        )

        event_handler.store_queued_events(None, None)

        self.assertEqual(mock_stdout.getvalue(), 'sample-id-1\nsample-id-2\n')
        self.assertEqual(self.__number_of_visible_messages(), '0')
        self.assertEqual(self.__number_of_hidden_messages(), '0')

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_does_not_delete_invalid_messages(self, mock_stdout):
        self.__send_messages_to_queue(
            [
                'invalid event',
                create_event_string('sample-id-2'),
            ]
        )

        event_handler.store_queued_events(None, None)

        self.assertRegex(mock_stdout.getvalue(), 'Failed to store message - Exception:')
        self.assertRegex(mock_stdout.getvalue(), 'sample-id-2')
        self.assertEqual(self.__number_of_visible_messages(), '0')
        self.assertEqual(self.__number_of_hidden_messages(), '1')

    def __send_messages_to_queue(self, messages):
        for message in messages:
            self.__sqs_client.send_message(
                QueueUrl=self.__queue_url,
                MessageBody=message,
                DelaySeconds=0
            )

    def __number_of_visible_messages(self):
        return self.__get_attribute('ApproximateNumberOfMessages')

    def __number_of_hidden_messages(self):
        return self.__get_attribute('ApproximateNumberOfMessagesNotVisible')

    def __get_attribute(self, attribute):
        response = self.__sqs_client.get_queue_attributes(
            QueueUrl=self.__queue_url,
            AttributeNames=[attribute]
        )
        return response['Attributes'][attribute]


def setup_stub_aws_config():
    os.environ = {
        'AWS_DEFAULT_REGION': 'eu-west-2',
    }


def create_queue(sqs_client):
    queue = sqs_client.create_queue(
        QueueName=str(uuid.uuid4()),
    )
    return queue['QueueUrl']


def add_queue_url_to_environment_variables(queue_url):
    os.environ['QUEUE_URL'] = queue_url


def create_event_string(event_id):
    return json.dumps({
        'eventId': event_id,
        'eventType': 'session_event',
        'timestamp': '2018-02-10:12:00:00',
        'details': {
            'sessionEventType': 'success'
        }
    })
