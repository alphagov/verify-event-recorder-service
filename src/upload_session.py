import datetime

class UploadSession(object):
    def __init__(self,
                 id=0,
                 time_stamp=None,
                 source_file_name=None,
                 idp_entity_id=None,
                 userid=None,
                 passed_validation=False):
        self.id = id
        if time_stamp:
            self.time_stamp = time_stamp
        else:
            self.time_stamp = datetime.datetime.now()

        self.source_file_name = source_file_name
        self.idp_entity_id = idp_entity_id
        self.userid = userid
        self.passed_validation = passed_validation
