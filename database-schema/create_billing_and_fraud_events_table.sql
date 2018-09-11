CREATE SCHEMA billing AUTHORIZATION postgres;

CREATE TABLE billing.billing_events
(
    time_stamp                   timestamp,
    session_id                   text COLLATE pg_catalog."default",
    hashed_persistent_id         text COLLATE pg_catalog."default",
    request_id                   text COLLATE pg_catalog."default",
    idp_entity_id                text COLLATE pg_catalog."default",
    minimum_level_of_assurance   text COLLATE pg_catalog."default",
    required_level_of_assurance  text COLLATE pg_catalog."default",
    provided_level_of_assurance  text COLLATE pg_catalog."default"
)
TABLESPACE pg_default;
ALTER TABLE billing.billing_events OWNER to postgres;

CREATE TABLE billing.fraud_events
(
    time_stamp            timestamp,
    session_id            text COLLATE pg_catalog."default",
    hashed_persistent_id  text COLLATE pg_catalog."default",
    request_id            text COLLATE pg_catalog."default",
    entity_id             text COLLATE pg_catalog."default",
    fraud_event_id        text COLLATE pg_catalog."default",
    fraud_indicator       text COLLATE pg_catalog."default"
)
TABLESPACE pg_default;
ALTER TABLE billing.fraud_events OWNER to postgres;