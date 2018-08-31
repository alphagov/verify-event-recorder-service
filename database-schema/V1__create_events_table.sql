CREATE TABLE events (
                    event_id TEXT NOT NULL PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    details JSONB NOT NULL
                );
