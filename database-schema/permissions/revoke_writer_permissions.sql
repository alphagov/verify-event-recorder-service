REVOKE USAGE ON SCHEMA audit FROM writer;
REVOKE USAGE ON SCHEMA billing FROM writer;
REVOKE SELECT, INSERT, DELETE ON audit.audit_events FROM writer;
REVOKE SELECT, INSERT, DELETE ON billing.billing_events FROM writer;
REVOKE SELECT, INSERT, DELETE ON billing.fraud_events FROM writer;
-- Production and staging only
REVOKE SELECT, INSERT, DELETE ON billing.billing_idps FROM writer;
