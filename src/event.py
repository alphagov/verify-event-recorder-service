import json

EVENT_ID = 'eventId'
EVENT_TYPE = 'eventType'
TIMESTAMP = 'timestamp'
DETAILS = 'details'
REQUIRED_FIELDS = [EVENT_ID, EVENT_TYPE, TIMESTAMP, DETAILS]


class Event(object):
    def __init__(self, event_id, timestamp, event_type, details):
        self.__event_id = event_id
        self.__timestamp = timestamp
        self.__event_type = event_type
        self.__details = details

    @property
    def event_id(self):
        return self.__event_id

    @property
    def timestamp(self):
        return self.__timestamp

    @property
    def event_type(self):
        return self.__event_type

    @property
    def details(self):
        return self.__details


def from_json(json_string):
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
