import json

from src.event import Event

EVENT_ID = 'eventId'
EVENT_TYPE = 'eventType'
TIMESTAMP = 'timestamp'
DETAILS = 'details'
REQUIRED_FIELDS = [EVENT_ID, EVENT_TYPE, TIMESTAMP, DETAILS]


def event_from_json(json_string):
    json_object = json.loads(json_string)
    __validate_json_object(json_object)
    return Event(
        event_id=json_object[EVENT_ID],
        timestamp=json_object[TIMESTAMP],
        event_type=json_object[EVENT_TYPE],
        details=json_object[DETAILS],
    )


def __validate_json_object(json_object):
    for field in REQUIRED_FIELDS:
        if field not in json_object:
            raise ValueError('Invalid Message. Missing required field "{0}"'.format(field))