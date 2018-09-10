CREATE SCHEMA audit AUTHORIZATION postgres;

CREATE TABLE audit.audit_events
(
    event_id             text COLLATE pg_catalog."default",
    time_stamp           timestamp,
    originating_service  text COLLATE pg_catalog."default",
    session_id           text COLLATE pg_catalog."default",
    event_type           text COLLATE pg_catalog."default",
    details              jsonb,
    PRIMARY KEY (event_id, time_stamp)
)
TABLESPACE pg_default;
ALTER TABLE audit.audit_events OWNER to postgres;

