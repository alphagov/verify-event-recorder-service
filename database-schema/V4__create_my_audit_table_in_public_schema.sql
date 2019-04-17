-- CREATE INDEX idx_session_event_type ON audit.audit_events((details->>'session_event_type'),(details->>'provided_level_of_assurance'),(details->>'pid'));
CREATE TABLE public.my_audit_events
(
    event_id             text COLLATE pg_catalog."default" NOT NULL,
    time_stamp           timestamp                         NOT NULL,
    originating_service  text COLLATE pg_catalog."default" NOT NULL,
    session_id           text COLLATE pg_catalog."default",
    event_type           text COLLATE pg_catalog."default" NOT NULL,
    details              jsonb,
    PRIMARY KEY (event_id, time_stamp)
)
TABLESPACE pg_default;
ALTER TABLE public.my_audit_events OWNER to postgres;
CREATE INDEX ON public.my_audit_events (time_stamp);
