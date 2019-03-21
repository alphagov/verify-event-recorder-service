GRANT USAGE ON SCHEMA audit TO iam_writer;
GRANT USAGE ON SCHEMA billing TO iam_writer;
GRANT SELECT, INSERT, DELETE ON audit.audit_events TO iam_writer;
GRANT SELECT, INSERT, DELETE ON billing.billing_events TO iam_writer;
GRANT SELECT, INSERT, DELETE ON billing.fraud_events TO iam_writer;
-- Production and staging only
GRANT SELECT, INSERT, DELETE ON billing.billing_idps TO iam_writer;
