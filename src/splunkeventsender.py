# the following allows JSON to be posted to Splunk HEC (HTTP Event Collector)

import logging
import os
import json
from src.kms import decrypt


class SplunkEventSender:
    def __init__(
        self,
        hec_token,
        hec_host,
        index="main",
        host=None,
        source=None,
        sourcetype="json",
        hec_port='443'
    ):
        self.index = index
        self.host = host
        self.source = source
        self.sourcetype = sourcetype
        self.hec_token = hec_token
        self.uri = f"https://{hec_host}:{hec_port}/services/collector"

    def base_json_event(self):
        return {
            "host": self.host,
            "source": self.source,
            "sourcetype": self.sourcetype,
            "index": self.index,
            "event": {},
        }

    def send(self, payload):
        logger = logging.getLogger('splunk-event-send')
        logger.setLevel(logging.INFO)

        headers = {
            'Authorization': f'Splunk {self.hec_token}',
            'Content-Type': 'application/json'
        }

        if isinstance(payload, str):
            payload = json.loads(payload)

        json_event = self.base_json_event()

        if "timestamp" in payload:
            json_event["time"] = payload["timestamp"]

        json_event["event"] = json.dumps(payload)

        event = str(json.dumps(json_event))

        try:
            r = requests.post(self.uri, data=event, headers=headers, verify=True)
            res = r.status_code, r.text,
        except Exception as e:
            logger.error("SplunkEventSender:send:", e)
            res = False
        return res


def push_event_to_splunk(event):
    logger = logging.getLogger('push-event-to-splunk')
    logger.setLevel(logging.INFO)

    if 'production' in os.environ['QUEUE_URL'] 

        for var in [
            "SPLUNK_HEC_TOKEN",
            "SPLUNK_HEC_HOST",
            "SPLUNK_HEC_PORT",
            "SPLUNK_HEC_INDEX",
        ]:
            if var not in os.environ:
                logger.info("'{0}' not set".format(var))
        try:
            s_tokn = decrypt(os.environ['SPLUNK_HEC_TOKEN']).decode()
        except Exception as e:
            logger.error("splunk-hec-token:failed-to-decrypt:", e)
            return  False

        s_host = os.environ['SPLUNK_HEC_HOST']
        s_port = os.environ['SPLUNK_HEC_PORT']
        s_indx = os.environ['SPLUNK_HEC_INDEX']

        if s_tokn and s_host and s_port and s_indx:
            hec = SplunkEventSender(
                hec_token=s_tokn,
                hec_host=s_host,
                hec_port=s_port,
                index=s_indx,
            )
            return hec.send(event)

    return False
