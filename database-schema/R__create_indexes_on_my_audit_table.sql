CREATE INDEX idx_billing_details_index ON public.my_audit_events((details->>'session_event_type'),(details->>'provided_level_of_assurance'),(details->>'pid'));
