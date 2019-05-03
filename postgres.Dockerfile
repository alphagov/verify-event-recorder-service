FROM postgres

RUN apt-get update && apt-get install -y git-core
RUN git clone --depth=1 https://github.com/alphagov/verify-event-system-database-scripts.git db-repo \
  && cp db-repo/migrations/*.sql /docker-entrypoint-initdb.d/
