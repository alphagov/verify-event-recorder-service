--
-- PostgreSQL database dump
--

-- Dumped from database version 10.6
-- Dumped by pg_dump version 11.2

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: audit; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA audit;


ALTER SCHEMA audit OWNER TO postgres;

--
-- Name: billing; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA billing;


ALTER SCHEMA billing OWNER TO postgres;

--
-- Name: default; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA "default";


ALTER SCHEMA "default" OWNER TO postgres;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: audit_events; Type: TABLE; Schema: audit; Owner: postgres
--

CREATE TABLE audit.audit_events (
    event_id text NOT NULL,
    time_stamp timestamp without time zone NOT NULL,
    originating_service text NOT NULL,
    session_id text,
    event_type text NOT NULL,
    details jsonb
);


ALTER TABLE audit.audit_events OWNER TO postgres;

--
-- Name: billing_events; Type: TABLE; Schema: billing; Owner: postgres
--

CREATE TABLE billing.billing_events (
    time_stamp timestamp without time zone NOT NULL,
    session_id text NOT NULL,
    hashed_persistent_id text NOT NULL,
    request_id text NOT NULL,
    idp_entity_id text NOT NULL,
    minimum_level_of_assurance text NOT NULL,
    required_level_of_assurance text NOT NULL,
    provided_level_of_assurance text NOT NULL
);


ALTER TABLE billing.billing_events OWNER TO postgres;

--
-- Name: billing_idps; Type: TABLE; Schema: billing; Owner: postgres
--

CREATE TABLE billing.billing_idps (
    "entityId" text NOT NULL
);


ALTER TABLE billing.billing_idps OWNER TO postgres;

--
-- Name: fraud_events; Type: TABLE; Schema: billing; Owner: postgres
--

CREATE TABLE billing.fraud_events (
    time_stamp timestamp without time zone NOT NULL,
    session_id text NOT NULL,
    hashed_persistent_id text NOT NULL,
    request_id text,
    entity_id text NOT NULL,
    fraud_event_id text NOT NULL,
    fraud_indicator text NOT NULL
);


ALTER TABLE billing.fraud_events OWNER TO postgres;

--
-- Name: flyway_schema_history; Type: TABLE; Schema: default; Owner: postgres
--

CREATE TABLE "default".flyway_schema_history (
    installed_rank integer NOT NULL,
    version character varying(50),
    description character varying(200) NOT NULL,
    type character varying(20) NOT NULL,
    script character varying(1000) NOT NULL,
    checksum integer,
    installed_by character varying(100) NOT NULL,
    installed_on timestamp without time zone DEFAULT now() NOT NULL,
    execution_time integer NOT NULL,
    success boolean NOT NULL
);


ALTER TABLE "default".flyway_schema_history OWNER TO postgres;

--
-- Name: audit_events audit_events_pkey; Type: CONSTRAINT; Schema: audit; Owner: postgres
--

ALTER TABLE ONLY audit.audit_events
    ADD CONSTRAINT audit_events_pkey PRIMARY KEY (event_id, time_stamp);


--
-- Name: flyway_schema_history flyway_schema_history_pk; Type: CONSTRAINT; Schema: default; Owner: postgres
--

ALTER TABLE ONLY "default".flyway_schema_history
    ADD CONSTRAINT flyway_schema_history_pk PRIMARY KEY (installed_rank);


--
-- Name: audit_events_event_id_idx1; Type: INDEX; Schema: audit; Owner: postgres
--

CREATE INDEX audit_events_event_id_idx1 ON audit.audit_events USING btree (event_id);


--
-- Name: audit_events_time_stamp_idx1; Type: INDEX; Schema: audit; Owner: postgres
--

CREATE INDEX audit_events_time_stamp_idx1 ON audit.audit_events USING btree (time_stamp);


--
-- Name: session_id_idx; Type: INDEX; Schema: audit; Owner: postgres
--

CREATE INDEX session_id_idx ON audit.audit_events USING btree (session_id);


--
-- Name: billing_events_hashed_persistent_id_idx1; Type: INDEX; Schema: billing; Owner: postgres
--

CREATE INDEX billing_events_hashed_persistent_id_idx1 ON billing.billing_events USING btree (hashed_persistent_id);


--
-- Name: billing_events_provided_level_of_assurance_idx1; Type: INDEX; Schema: billing; Owner: postgres
--

CREATE INDEX billing_events_provided_level_of_assurance_idx1 ON billing.billing_events USING btree (provided_level_of_assurance);


--
-- Name: billing_events_session_id_idx1; Type: INDEX; Schema: billing; Owner: postgres
--

CREATE INDEX billing_events_session_id_idx1 ON billing.billing_events USING btree (session_id);


--
-- Name: billing_events_time_stamp_idx1; Type: INDEX; Schema: billing; Owner: postgres
--

CREATE INDEX billing_events_time_stamp_idx1 ON billing.billing_events USING btree (time_stamp);


--
-- Name: fraud_events_hashed_persistent_id_idx1; Type: INDEX; Schema: billing; Owner: postgres
--

CREATE INDEX fraud_events_hashed_persistent_id_idx1 ON billing.fraud_events USING btree (hashed_persistent_id);


--
-- Name: fraud_events_session_id_idx; Type: INDEX; Schema: billing; Owner: postgres
--

CREATE INDEX fraud_events_session_id_idx ON billing.fraud_events USING btree (session_id);


--
-- Name: fraud_events_time_stamp_idx1; Type: INDEX; Schema: billing; Owner: postgres
--

CREATE INDEX fraud_events_time_stamp_idx1 ON billing.fraud_events USING btree (time_stamp);


--
-- Name: flyway_schema_history_s_idx; Type: INDEX; Schema: default; Owner: postgres
--

CREATE INDEX flyway_schema_history_s_idx ON "default".flyway_schema_history USING btree (success);


--
-- Name: SCHEMA audit; Type: ACL; Schema: -; Owner: postgres
--

GRANT USAGE ON SCHEMA audit TO iam_reader;
GRANT USAGE ON SCHEMA audit TO iam_writer;


--
-- Name: SCHEMA billing; Type: ACL; Schema: -; Owner: postgres
--

GRANT USAGE ON SCHEMA billing TO iam_reader;
GRANT USAGE ON SCHEMA billing TO iam_writer;


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE ALL ON SCHEMA public FROM rdsadmin;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- Name: TABLE audit_events; Type: ACL; Schema: audit; Owner: postgres
--

GRANT SELECT ON TABLE audit.audit_events TO iam_reader;
GRANT SELECT,INSERT,DELETE ON TABLE audit.audit_events TO iam_writer;


--
-- Name: TABLE billing_events; Type: ACL; Schema: billing; Owner: postgres
--

GRANT SELECT ON TABLE billing.billing_events TO iam_reader;
GRANT SELECT,INSERT,DELETE ON TABLE billing.billing_events TO iam_writer;


--
-- Name: TABLE billing_idps; Type: ACL; Schema: billing; Owner: postgres
--

GRANT SELECT ON TABLE billing.billing_idps TO iam_reader;
GRANT SELECT,INSERT,DELETE ON TABLE billing.billing_idps TO iam_writer;


--
-- Name: TABLE fraud_events; Type: ACL; Schema: billing; Owner: postgres
--

GRANT SELECT ON TABLE billing.fraud_events TO iam_reader;
GRANT SELECT,INSERT,DELETE ON TABLE billing.fraud_events TO iam_writer;


--
-- PostgreSQL database dump complete
--

