GRANT USAGE ON SCHEMA audit TO iam_reader;
GRANT USAGE ON SCHEMA billing TO iam_reader;
GRANT SELECT ON audit.audit_events TO iam_reader;
GRANT SELECT ON billing.billing_events TO iam_reader;
GRANT SELECT ON billing.fraud_events TO iam_reader;
-- Production and staging only
-- GRANT SELECT ON billing.billing_idps TO iam_reader;
