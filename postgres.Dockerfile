FROM postgres

RUN apt-get update
RUN apt-get install -y git-core

RUN git clone --depth=1 https://github.com/alphagov/verify-event-system-database-scripts.git db-repo
RUN cp db-repo/migrations/*.sql /docker-entrypoint-initdb.d/
