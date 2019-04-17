REVOKE ALL PRIVILEGES ON DATABASE events FROM iam_reader;
REVOKE CONNECT ON DATABASE events FROM iam_reader;
REVOKE ALL ON billing.fraud_events FROM iam_reader;
REVOKE ALL ON billing.billing_events FROM iam_reader;
REVOKE ALL ON audit.audit_events FROM iam_reader;
REVOKE ALL ON SCHEMA billing FROM iam_reader;
REVOKE ALL ON SCHEMA audit FROM iam_reader;
-- Production and staging only
REVOKE ALL ON billing.billing_idps FROM reader;
