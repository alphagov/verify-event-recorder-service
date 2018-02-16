import json
from json import JSONDecodeError
from unittest import TestCase

from src.event import from_json

EVENT_ID = '1234-abcd'
EVENT_TYPE = 'session_event'
TIMESTAMP = '2018-02-10:12:00:00'
SESSION_EVENT_TYPE = 'success'


class EventTest(TestCase):

    def test_can_create_event_from_valid_message_string(self):
        json_string = json.dumps(valid_message_object())

        event = from_json(json_string)

        self.assertEqual(event.event_id, EVENT_ID)
        self.assertEqual(event.event_type, EVENT_TYPE)
        self.assertEqual(event.timestamp, TIMESTAMP)
        self.assertEqual(event.details['sessionEventType'], SESSION_EVENT_TYPE)

    def test_ignores_additional_elements_in_json_string(self):
        message_object = valid_message_object()
        message_object['foo'] = 'bar'
        json_string = json.dumps(message_object)

        event = from_json(json_string)

        self.assertEqual(event.event_id, EVENT_ID)
        self.assertEqual(event.event_type, EVENT_TYPE)
        self.assertEqual(event.timestamp, TIMESTAMP)
        self.assertEqual(event.details['sessionEventType'], SESSION_EVENT_TYPE)

    def test_throws_validation_exception_if_required_element_is_missing(self):
        required_elements = [
            'eventId',
            'eventType',
            'timestamp',
            'details',
        ]

        for element in required_elements:
            message_object = valid_message_object()
            message_object.pop(element)
            json_string = json.dumps(message_object)

            with self.assertRaises(ValueError) as raised_exception:
                from_json(json_string)

            self.assertEqual(
                str(raised_exception.exception),
                'Invalid Message. Missing required field "{0}"'.format(element)
            )

    def test_throws_validation_exception_if_string_is_not_valid_json(self):
        with self.assertRaises(JSONDecodeError):
            from_json('not valid')


def valid_message_object():
    return {
        'eventId': EVENT_ID,
        'eventType': EVENT_TYPE,
        'timestamp': TIMESTAMP,
        'details': {
            'sessionEventType': SESSION_EVENT_TYPE
        }
    }
