import json
import dateutil.parser
from src.event import Event

EVENT_ID = 'eventId'
EVENT_TYPE = 'eventType'
TIMESTAMP = 'timestamp'
ORIGINATING_SERVICE = 'originatingService'
SESSION_ID = 'sessionId'
DETAILS = 'details'
REQUIRED_FIELDS = [EVENT_ID, EVENT_TYPE, TIMESTAMP, ORIGINATING_SERVICE, DETAILS]


def event_from_json(json_string):
    json_object = json.loads(json_string)
    return event_from_json_object(json_object)


def event_from_json_object(json_object):
    __validate_json_object(json_object)
    if json_object[EVENT_TYPE] == 'error_event' and SESSION_ID not in json_object:
        return Event(
            event_id=json_object[EVENT_ID],
            timestamp=__date_checker(json_object[TIMESTAMP]),
            event_type=json_object[EVENT_TYPE],
            originating_service=json_object[ORIGINATING_SERVICE],
            session_id='',
            details=json_object[DETAILS],
        )
    return Event(
        event_id=json_object[EVENT_ID],
        timestamp=__date_checker(json_object[TIMESTAMP]),
        event_type=json_object[EVENT_TYPE],
        originating_service=json_object[ORIGINATING_SERVICE],
        session_id=json_object[SESSION_ID],
        details=json_object[DETAILS],
    )


def __validate_json_object(json_object):
    for field in REQUIRED_FIELDS:
        if field not in json_object:
            raise ValueError('Invalid Message. Missing required field "{0}"'.format(field))


def __date_checker(date_time):
    if isinstance(date_time, str):
        return int(dateutil.parser.parse(date_time).timestamp() * 1000)

    return date_time
