REVOKE ALL PRIVILEGES ON DATABASE events FROM reader;
REVOKE CONNECT ON DATABASE events FROM reader;
REVOKE ALL ON billing.fraud_events FROM reader;
REVOKE ALL ON billing.billing_events FROM reader;
REVOKE ALL ON audit.audit_events FROM reader;
REVOKE ALL ON SCHEMA billing FROM reader;
REVOKE ALL ON SCHEMA audit FROM reader;
-- Production and staging only
REVOKE ALL ON billing.billing_idps FROM reader;
