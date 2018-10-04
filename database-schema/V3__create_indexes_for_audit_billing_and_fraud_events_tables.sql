CREATE INDEX ON audit.audit_events (event_id);
CREATE INDEX ON billing.billing_events (session_id);
CREATE INDEX ON billing.fraud_events (session_id);
