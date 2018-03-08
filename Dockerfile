FROM python:latest

RUN apt-get update && apt-get install -y postgresql postgresql-contrib sudo unzip

COPY build/docker-entry.sh /usr/local/bin/
COPY requirements/*.txt /usr/local/bin/requirements/

RUN ./usr/local/bin/docker-entry.sh