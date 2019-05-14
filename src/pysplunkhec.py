# the following allows JSON to be posted to Splunk HEC (HTTP Event Collector)

import os
import requests
import json
from src.kms import decrypt

class PySplunkHEC:
    def __init__(
        self,
        hec_token,
        hec_host,
        index="main",
        host="null",
        source="null",
        sourcetype="json",
        hec_port='443'
        ):
        self.index = index
        self.host = host
        self.source = source
        self.sourcetype = sourcetype
        self.hec_token = hec_token
        self.uri = "https://" + hec_host + ":" + hec_port + "/services/collector"

    def base_json_event(self):
        return {
            "host": self.host,
            "source": self.source,
            "sourcetype": self.sourcetype,
            "index": self.index,
            "event": {},
            }

    def send(self, payload):
        headers = {
            'Authorization': 'Splunk ' + self.hec_token,
            'Content-Type': 'application/json'
            }

        if isinstance(payload, str):
            payload = json.loads(payload)

        json_event = self.base_json_event()

        if "timestamp" in payload:
            json_event["time"] = payload["timestamp"]

        json_event["event"] = json.dumps(payload)

        event = str(json.dumps(json_event))

        res = False
        try:
            r = requests.post(self.uri, data=event, headers=headers, verify=True)
            res = r.status_code, r.text,
        except Exception as e:
            print("PySplunkHEC:send:", e)
            res = False
        return res

def push_event_to_splunk(event):
    have_vars = True
    for var in [
        "SPLUNK_HEC_TOKEN",
        "SPLUNK_HEC_HOST",
        "SPLUNK_HEC_PORT",
        "SPLUNK_HEC_INDEX",
        ]:
        if var not in os.environ:
            raise Exception("'{0}' not set".format(var))
            have_vars = False

    if have_vars:
        s_tokn = decrypt(os.environ['SPLUNK_HEC_TOKEN']).decode()
        s_host = os.environ['SPLUNK_HEC_HOST']
        s_port = os.environ['SPLUNK_HEC_PORT']
        s_indx = os.environ['SPLUNK_HEC_INDEX']

        if s_tokn and s_host and s_port and s_indx:
            hec = PySplunkHEC(
                hec_token=s_tokn,
                hec_host=s_host,
                hec_port=s_port,
                index=s_indx,
            )
            return hec.send(event)

    return False
