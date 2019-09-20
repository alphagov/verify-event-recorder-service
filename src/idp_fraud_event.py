class IdpFraudEvent(object):
    def __init__(self,
                 idp_entity_id,
                 idp_event_id,
                 timestamp,
                 fid_code,
                 request_id,
                 pid,
                 client_ip_address,
                 contra_score,
                 contra_indicators=[]):
        self.idp_entity_id = idp_entity_id
        self.idp_event_id = idp_event_id
        self.timestamp = timestamp
        self.fid_code = fid_code
        self.request_id = request_id
        self.pid = pid
        self.client_ip_address = client_ip_address
        self.contra_score = contra_score
        if contra_indicators:
            self.contra_indicators = contra_indicators
        else:
            self.contra_indicators = []
